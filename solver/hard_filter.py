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
        
        CRITICAL: Zero tolerance - any constraint violation excludes the part.
        
        Args:
            spec: Requirement specification
        
        Returns:
            List of parts satisfying ALL hard constraints
        """
        logger.info("Applying hard filter")
        
        # Compile constraints to SQL
        where_clause, params = self.compiler.compile(spec)
        
        # Build query
        query = f"""
        SELECT 
            p.id,
            p.mpn,
            p.manufacturer,
            p.family,
            p.status,
            p.package_family,
            p.package_name,
            p.pin_count,
            p.temp_min_c,
            p.temp_max_c,
            m.core,
            m.max_mhz,
            m.flash_kb,
            m.sram_kb,
            m.eeprom_kb,
            m.can_count,
            m.can_fd_count,
            m.uart_count,
            m.spi_count,
            m.i2c_count,
            m.usb_fs,
            m.usb_hs,
            m.ethernet,
            m.adc_channels,
            m.dac_channels,
            m.timers_count,
            m.pwm_channels,
            m.has_fpu,
            m.has_dsp,
            m.has_crypto,
            m.has_wireless,
            m.vdd_min_v,
            m.vdd_max_v,
            m.active_ma,
            m.standby_ua,
            m.sleep_ua,
            m.cost_usd,
            m.extras
        FROM parts p
        JOIN mcu_specs m ON p.id = m.part_id
        WHERE {where_clause}
        ORDER BY p.mpn ASC  -- Deterministic ordering for tie-breaking
        """
        
        # Execute query
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, **params)
        
        logger.info(f"Hard filter: {len(rows)} candidates found")
        
        # Convert to dicts
        candidates = [dict(row) for row in rows]
        
        return candidates
    
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
