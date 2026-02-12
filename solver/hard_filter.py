"""
Hard Filter

Deterministic constraint satisfaction filter with zero tolerance for violations.
"""

import logging
from typing import List, Dict, Any
import asyncpg
from uuid import UUID

from core.models import RequirementSpec, PartBase, MCUSpecBase
from .compiler import ConstraintCompiler

logger = logging.getLogger(__name__)


class HardFilter:
    """Deterministic hard constraint filter"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize hard filter.
        
        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool
        self.compiler = ConstraintCompiler()
    
    async def filter(
        self,
        spec: RequirementSpec,
    ) -> List[Dict[str, Any]]:
        """
        Filter parts by hard constraints.
        Supports polymorphic component types (mcu, ldo, pmic, etc).
        """
        # Determine component type from constraints (injected by LLM or user)
        c_type = spec.hard_constraints.get('component_type', 'mcu').lower()
        logger.info(f"Applying hard filter for component_type: {c_type}")
        
        # Compile constraints
        where_clause, params = self.compiler.compile(spec)
        
        # Dispatch query builder
        if c_type == 'mcu':
            query = self._build_mcu_query(where_clause)
        elif c_type == 'ldo':
            query = self._build_ldo_query(where_clause)
        elif c_type == 'pmic':
            query = self._build_pmic_query(where_clause)
        elif c_type == 'can':
            query = self._build_can_query(where_clause)
        elif c_type == 'sensor':
            query = self._build_sensor_query(where_clause)
        elif c_type == 'passive':
            query = self._build_passive_query(where_clause)
        else:
             logger.warning(f"Unknown component type '{c_type}', defaulting to MCU")
             query = self._build_mcu_query(where_clause)
        
        # Execute
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        logger.info(f"Hard filter: {len(rows)} candidates found")
        
        # Hydrate candidates (nest specs for MLRanking)
        candidates = []
        for row in rows:
            r = dict(row)
            # Create nested specs dict if not present (MLRanking expects 'specs' key)
            # We move all non-PartBase fields into 'specs'
            part_keys = {'id', 'mpn', 'manufacturer', 'family', 'status', 'package_family', 'package_name', 'pin_count', 'temp_min_c', 'temp_max_c', 'datasheet_url'}
            specs = {k: v for k, v in r.items() if k not in part_keys}
            r['specs'] = specs
            # Ensure cost_usd exists for ranking (default to 0 if missing)
            if 'cost_usd' not in r:
                r['cost_usd'] = 0.0
            candidates.append(r)
            
        return candidates

    def _build_mcu_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family, p.package_name,
            p.pin_count, p.temp_min_c, p.temp_max_c,
            m.core, m.max_mhz, m.flash_kb, m.sram_kb, m.eeprom_kb,
            m.can_count, m.uart_count, m.spi_count, m.i2c_count,
            m.usb_fs, m.usb_hs, m.ethernet, m.adc_channels, m.dac_channels,
            m.has_fpu, m.has_dsp, m.has_wireless, m.cost_usd
        FROM parts p
        JOIN mcu_specs m ON p.id = m.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """

    def _build_ldo_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family, p.package_name,
            l.vin_min_v, l.vin_max_v, l.vout_type, l.vout_fixed_v, l.vout_min_v, l.vout_max_v,
            l.iout_max_ma, l.dropout_voltage_v, l.psrr_db, l.noise_uv_rms
        FROM parts p
        JOIN ldo_specs l ON p.id = l.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """

    def _build_pmic_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family,
            pm.input_voltage_min_v, pm.input_voltage_max_v,
            pm.buck_count, pm.ldo_count, pm.boost_count,
            pm.automotive_grade, pm.interfaces
        FROM parts p
        JOIN pmic_specs pm ON p.id = pm.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """

    def _build_can_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family,
            c.data_rate_mbps, c.supply_voltage_v, c.has_standby_mode,
            c.protection_features
        FROM parts p
        JOIN can_specs c ON p.id = c.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """

    def _build_sensor_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family,
            s.sensor_type, s.interface, s.supply_voltage_min_v, s.supply_voltage_max_v,
            s.resolution_bits
        FROM parts p
        JOIN sensor_specs s ON p.id = s.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """

    def _build_passive_query(self, where_clause: str) -> str:
        return f"""
        SELECT 
            p.id, p.mpn, p.manufacturer, p.family, p.status, p.package_family,
            psv.type, psv.value_primary, psv.tolerance_percent,
            psv.power_rating_w, psv.voltage_rating_v, psv.package_case
        FROM parts p
        JOIN passive_specs psv ON p.id = psv.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC
        """
    
    async def count_total_parts(self) -> int:
        """Count total parts in database"""
        query = "SELECT COUNT(*) FROM parts"
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval(query)
        
        return result
    
    async def verify_constraint_satisfaction(
        self,
        part_id: UUID,
        spec: RequirementSpec,
    ) -> Dict[str, bool]:
        """
        Verify which constraints a part satisfies (for debugging/explanation).
        
        Args:
            part_id: Part ID to check
            spec: Requirement specification
        
        Returns:
            Dict of constraint_name -> satisfied (bool)
        """
        # Fetch part data
        query = """
        SELECT 
            p.*,
            m.*
        FROM parts p
        JOIN mcu_specs m ON p.id = m.part_id
        WHERE p.id = $1
        """
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, part_id)
        
        if not row:
            return {}
        
        part_data = dict(row)
        
        # Check each constraint
        satisfaction = {}
        
        for field_name, constraint_value in spec.hard_constraints.items():
            satisfied = self._check_constraint(part_data, field_name, constraint_value)
            satisfaction[field_name] = satisfied
        
        return satisfaction
    
    def _check_constraint(
        self,
        part_data: Dict[str, Any],
        field_name: str,
        constraint_value: Any,
    ) -> bool:
        """Check if a single constraint is satisfied"""
        # Map field names to data keys
        field_map = {
            'core': 'core',
            'core_architecture': 'core',
            'flash_kb': 'flash_kb',
            'ram_kb': 'sram_kb',
            'sram_kb': 'sram_kb',
            'clock_mhz': 'max_mhz',
            'max_mhz': 'max_mhz',
            'can_count': 'can_count',
            'can_fd_count': 'can_fd_count',
            'package_family': 'package_family',
            'package': 'package_family',
            'has_fpu': 'has_fpu',
            'has_wireless': 'has_wireless',
        }
        
        data_key = field_map.get(field_name, field_name)
        actual_value = part_data.get(data_key)
        
        if actual_value is None:
            return False
        
        # Check constraint type
        if isinstance(constraint_value, dict):
            # Range constraint
            if "min" in constraint_value and actual_value < constraint_value["min"]:
                return False
            if "max" in constraint_value and actual_value > constraint_value["max"]:
                return False
            return True
        
        elif isinstance(constraint_value, list):
            # IN constraint
            return actual_value in constraint_value
        
        else:
            # Equality constraint
            return actual_value == constraint_value
