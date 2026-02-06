"""
Constraint Compiler

Compile RequirementSpec into SQL WHERE clauses for deterministic filtering.
"""

import logging
from typing import Dict, List, Tuple, Any
from core.models import RequirementSpec

logger = logging.getLogger(__name__)


class ConstraintCompiler:
    """Compile requirements into SQL queries"""
    
    def compile(self, spec: RequirementSpec) -> Tuple[str, Dict[str, Any]]:
        """
        Compile RequirementSpec into SQL WHERE clause and parameters.
        
        Args:
            spec: Requirement specification
        
        Returns:
            Tuple of (where_clause, parameters_dict)
        """
        where_clauses = []
        params = {}
        param_counter = 0
        
        # Compile hard constraints
        for field_name, constraint_value in spec.hard_constraints.items():
            clause, field_params = self._compile_constraint(
                field_name,
                constraint_value,
                param_counter,
            )
            
            if clause:
                where_clauses.append(clause)
                params.update(field_params)
                param_counter += len(field_params)
        
        # Compile environment constraints (temp range)
        if spec.environment:
            for field_name, constraint_value in spec.environment.items():
                clause, field_params = self._compile_constraint(
                    field_name,
                    constraint_value,
                    param_counter,
                )
                
                if clause:
                    where_clauses.append(clause)
                    params.update(field_params)
                    param_counter += len(field_params)
        
        # Compile interface requirements
        if spec.interfaces:
            for peripheral, min_count in spec.interfaces.items():
                field_name = f"{peripheral}_count"
                clause, field_params = self._compile_constraint(
                    field_name,
                    {"min": min_count},
                    param_counter,
                )
                
                if clause:
                    where_clauses.append(clause)
                    params.update(field_params)
                    param_counter += len(field_params)
        
        # Join all clauses
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        return where_sql, params
    
    def _compile_constraint(
        self,
        field_name: str,
        constraint_value: Any,
        param_counter: int,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Compile a single constraint into SQL.
        
        Returns:
            Tuple of (clause, parameters)
        """
        # Map field names to database columns
        field_map = {
            'core': 'mcu_specs.core',
            'core_architecture': 'mcu_specs.core',
            'flash_kb': 'mcu_specs.flash_kb',
            'ram_kb': 'mcu_specs.sram_kb',
            'sram_kb': 'mcu_specs.sram_kb',
            'clock_mhz': 'mcu_specs.max_mhz',
            'max_mhz': 'mcu_specs.max_mhz',
            'can_count': 'mcu_specs.can_count',
            'can_fd_count': 'mcu_specs.can_fd_count',
            'uart_count': 'mcu_specs.uart_count',
            'spi_count': 'mcu_specs.spi_count',
            'i2c_count': 'mcu_specs.i2c_count',
            'usb_fs': 'mcu_specs.usb_fs',
            'usb_hs': 'mcu_specs.usb_hs',
            'ethernet': 'mcu_specs.ethernet',
            'has_fpu': 'mcu_specs.has_fpu',
            'has_wireless': 'mcu_specs.has_wireless',
            'package_family': 'parts.package_family',
            'package': 'parts.package_family',
            'pin_count': 'parts.pin_count',
            'temp_min_c': 'parts.temp_min_c',
            'temp_max_c': 'parts.temp_max_c',
            'status': 'parts.status',
            'manufacturer': 'parts.manufacturer',
            'cost_usd': 'mcu_specs.cost_usd',
        }
        
        db_field = field_map.get(field_name)
        if not db_field:
            logger.warning(f"Unknown field: {field_name}")
            return "", {}
        
        params = {}
        
        # Handle different constraint types
        if isinstance(constraint_value, dict):
            # Range constraint: {"min": 128, "max": 512}
            clauses = []
            
            if "min" in constraint_value:
                param_name = f"param_{param_counter}"
                clauses.append(f"{db_field} >= :{param_name}")
                params[param_name] = constraint_value["min"]
                param_counter += 1
            
            if "max" in constraint_value:
                param_name = f"param_{param_counter}"
                clauses.append(f"{db_field} <= :{param_name}")
                params[param_name] = constraint_value["max"]
                param_counter += 1
            
            clause = " AND ".join(clauses)
        
        elif isinstance(constraint_value, list):
            # IN constraint: ["QFP", "QFN"]
            param_names = []
            for i, value in enumerate(constraint_value):
                param_name = f"param_{param_counter}_{i}"
                param_names.append(f":{param_name}")
                params[param_name] = value
            
            clause = f"{db_field} IN ({', '.join(param_names)})"
        
        elif isinstance(constraint_value, bool):
            # Boolean constraint
            param_name = f"param_{param_counter}"
            clause = f"{db_field} = :{param_name}"
            params[param_name] = constraint_value
        
        else:
            # Equality constraint
            param_name = f"param_{param_counter}"
            clause = f"{db_field} = :{param_name}"
            params[param_name] = constraint_value
        
        return clause, params
    
    def compile_for_count(self, spec: RequirementSpec) -> Tuple[str, Dict[str, Any]]:
        """
        Compile constraints for counting total parts in database.
        
        Returns:
            Tuple of (where_clause, parameters)
        """
        # For count, we only need basic filters (no joins needed)
        return self.compile(spec)
