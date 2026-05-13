"""
Constraint Compiler

Compile RequirementSpec into SQL WHERE clauses for deterministic filtering.
"""

from __future__ import annotations
import logging
from typing import Dict, List, Tuple, Any
from core.models import RequirementSpec

logger = logging.getLogger(__name__)


class ConstraintCompiler:
    """Compile requirements into SQL queries"""

    # Fields where a small fuzzy tolerance (2%) is acceptable
    CONTINUOUS_FIELDS: set = {'m.flash_kb', 'm.sram_kb', 'm.max_mhz', 'm.cost_usd'}
    
    def compile(self, spec: RequirementSpec) -> Tuple[str, List[Any]]:
        """
        Compile RequirementSpec into SQL WHERE clause and parameters.
        
        Args:
            spec: Requirement specification
        
        Returns:
            Tuple of (where_clause, parameters_list) for asyncpg
        """
        where_clauses = []
        params = []
        param_counter = 1  # asyncpg uses 1-indexed positional params
        
        # Compile hard constraints
        for field_name, constraint_value in spec.hard_constraints.items():
            clause, field_params, param_counter = self._compile_constraint(
                field_name,
                constraint_value,
                param_counter,
            )
            
            if clause:
                where_clauses.append(clause)
                params.extend(field_params)
        
        # Compile environment constraints (temp range)
        if spec.environment:
            for field_name, constraint_value in spec.environment.items():
                clause, field_params, param_counter = self._compile_constraint(
                    field_name,
                    constraint_value,
                    param_counter,
                )
                
                if clause:
                    where_clauses.append(clause)
                    params.extend(field_params)
        
        # Compile interface requirements
        if spec.interfaces:
            for peripheral, min_count in spec.interfaces.items():
                # Normalise: if user already sent 'can_count', don't double-suffix it
                if peripheral.endswith('_count'):
                    field_name = peripheral
                else:
                    field_name = f"{peripheral}_count"
                clause, field_params, param_counter = self._compile_constraint(
                    field_name,
                    {"min": min_count},
                    param_counter,
                )

                if clause:
                    where_clauses.append(clause)
                    params.extend(field_params)
        
        # Join all clauses
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        return where_sql, params
    
    def _compile_constraint(
        self,
        field_name: str,
        constraint_value: Any,
        param_counter: int,
    ) -> Tuple[str, List[Any], int]:
        """
        Compile a single constraint into SQL with positional parameters.
        
        Returns:
            Tuple of (clause, parameters_list, updated_param_counter)
        """
        # Map field names to database columns
        field_map = {
            # MCUs
            'core': 'm.core',
            'core_architecture': 'm.core',
            'flash_kb': 'm.flash_kb',
            'ram_kb': 'm.sram_kb',
            'sram_kb': 'm.sram_kb',
            'clock_mhz': 'm.max_mhz',
            'max_mhz': 'm.max_mhz',
            'can_count': 'm.can_count',
            'can_fd_count': 'm.can_fd_count',
            'uart_count': 'm.uart_count',
            'spi_count': 'm.spi_count',
            'i2c_count': 'm.i2c_count',
            'usb_fs': 'm.usb_fs',
            'usb_hs': 'm.usb_hs',
            'ethernet': 'm.ethernet',
            'has_fpu': 'm.has_fpu',
            'has_wireless': 'm.has_wireless',
            'cost_usd': 'm.cost_usd',

            # LDOs
            'ldo_vin_min': 'l.vin_min_v',
            'ldo_vin_max': 'l.vin_max_v',
            'ldo_vout': 'l.vout_fixed_v',
            'ldo_iout': 'l.iout_max_ma',
            'dropout': 'l.dropout_voltage_mv',
            'psrr': 'l.psrr_db',
            'noise': 'l.output_noise_uv',

            # PMICs
            'buck_count': 'pm.buck_count',
            'ldo_count': 'pm.ldo_count', 
            'input_voltage_min': 'pm.input_voltage_min_v',
            'input_voltage_max': 'pm.input_voltage_max_v',
            'automotive_grade': 'pm.automotive_grade',

            # CAN
            'data_rate': 'c.data_rate_mbps',
            'can_supply': 'c.supply_voltage_v',
            'standby_mode': 'c.has_standby_mode',

            # Sensors
            'sensor_type': 's.sensor_type',
            'interface': 's.interface',
            'resolution': 's.resolution_bits',

            # Passives
            # Passives (Partial support - schema varies by type)
            'passive_type': 'psv.type',
            'power_rating': 'psv.power_rating_w',

            # Common
            'package_family': 'p.package_family',
            'package': 'p.package_family',
            'pin_count': 'p.pin_count',
            'temp_min_c': 'p.temp_min_c',
            'temp_max_c': 'p.temp_max_c',
            'status': 'p.status',
            'manufacturer': 'p.manufacturer',
        }
        
        db_field = field_map.get(field_name)
        if not db_field:
            logger.warning(f"Unknown field: {field_name}")
            return "", [], param_counter
        
        params = []
        
        # Handle different constraint types
        if isinstance(constraint_value, dict):
            # Range constraint: {"min": 128, "max": 512}
            clauses = []
            
            if "min" in constraint_value:
                raw_val = constraint_value["min"]
                try: 
                    num_val = float(raw_val)
                    if db_field in self.CONTINUOUS_FIELDS:
                        fuzzy_min = num_val * 0.98
                        clauses.append(f"CAST({db_field} AS NUMERIC) >= ${param_counter}")
                        params.append(fuzzy_min)
                    else:
                        clauses.append(f"CAST({db_field} AS NUMERIC) >= ${param_counter}")
                        params.append(num_val)
                except:
                    clauses.append(f"CAST({db_field} AS NUMERIC) >= ${param_counter}")
                    params.append(raw_val)
                param_counter += 1
            
            if "max" in constraint_value:
                clauses.append(f"CAST({db_field} AS NUMERIC) <= ${param_counter}")
                val = constraint_value["max"]
                try: params.append(float(val) if '.' in str(val) else int(val))
                except: params.append(val)
                param_counter += 1
            
            clause = " AND ".join(clauses)
        
        elif isinstance(constraint_value, list):
            # IN constraint: ["QFP", "QFN"]
            param_placeholders = []
            for value in constraint_value:
                param_placeholders.append(f"${param_counter}")
                params.append(value)
                param_counter += 1
            
            clause = f"{db_field} IN ({', '.join(param_placeholders)})"
        
        elif isinstance(constraint_value, bool):
            # Boolean constraint
            clause = f"{db_field} = ${param_counter}"
            params.append(constraint_value)
            param_counter += 1
        
        else:
            # Equality constraint
            clause = f"{db_field} = ${param_counter}"
            params.append(constraint_value)
            param_counter += 1
        
        return clause, params, param_counter
    
    def compile_for_count(self, spec: RequirementSpec) -> Tuple[str, List[Any]]:
        """
        Compile constraints for counting total parts in database.
        
        Returns:
            Tuple of (where_clause, parameters_list)
        """
        # For count, we only need basic filters (no joins needed)
        return self.compile(spec)
