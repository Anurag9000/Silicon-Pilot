"""
Near-Miss Engine

Detect candidates that fail exactly one constraint and suggest relaxations.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional

from core.models import RequirementSpec, NearMissSuggestion

logger = logging.getLogger(__name__)


class NearMissEngine:
    """Near-miss detection and suggestion generation"""
    
    def __init__(self):
        """Initialize near-miss engine"""
        pass
    
    async def find_near_misses(
        self,
        spec: RequirementSpec,
        all_parts: List[Dict[str, Any]],
        valid_parts: List[Dict[str, Any]],
        max_suggestions: int = 5,
    ) -> List[NearMissSuggestion]:
        """
        Find parts that fail exactly one constraint.
        
        Args:
            spec: Requirement specification
            all_parts: All parts in database
            valid_parts: Parts that pass all constraints
            max_suggestions: Maximum suggestions to return
        
        Returns:
            List of near-miss suggestions
        """
        logger.info("Finding near-miss candidates")
        
        # Get parts that failed (not in valid set)
        valid_mpns = {p['mpn'] for p in valid_parts}
        failed_parts = [p for p in all_parts if p['mpn'] not in valid_mpns]
        
        if not failed_parts:
            return []
        
        # Check each failed part
        near_misses = []
        
        for part in failed_parts:
            # Check which constraints failed
            failed_constraints = self._check_constraints(part, spec)
            
            # Only consider parts that fail exactly 1 constraint
            if len(failed_constraints) == 1:
                constraint_name, required, actual = failed_constraints[0]
                
                # Generate suggestion
                suggestion = self._generate_suggestion(
                    part,
                    constraint_name,
                    required,
                    actual,
                )
                
                if suggestion:
                    near_misses.append(suggestion)
        
        # Sort by "closeness" (how small the gap is)
        near_misses.sort(key=lambda x: x.gap_size if x.gap_size else float('inf'))
        
        logger.info(f"Found {len(near_misses)} near-miss candidates")
        
        return near_misses[:max_suggestions]
    
    def _check_constraints(
        self,
        part: Dict[str, Any],
        spec: RequirementSpec,
    ) -> List[Tuple[str, Any, Any]]:
        """
        Check which constraints a part fails.
        
        Returns:
            List of (constraint_name, required_value, actual_value) tuples
        """
        failed = []
        
        # Check hard constraints
        for field_name, constraint_value in spec.hard_constraints.items():
            actual_value = part.get(field_name)
            
            if not self._satisfies_constraint(actual_value, constraint_value):
                failed.append((field_name, constraint_value, actual_value))
        
        # Check interface requirements
        if spec.interfaces:
            for peripheral, min_count in spec.interfaces.items():
                field_name = f"{peripheral}_count"
                actual_value = part.get(field_name, 0)
                
                if actual_value < min_count:
                    failed.append((field_name, {"min": min_count}, actual_value))
        
        # Check environment constraints
        if spec.environment:
            for field_name, constraint_value in spec.environment.items():
                actual_value = part.get(field_name)
                
                if not self._satisfies_constraint(actual_value, constraint_value):
                    failed.append((field_name, constraint_value, actual_value))
        
        return failed
    
    def _satisfies_constraint(
        self,
        actual_value: Any,
        constraint_value: Any,
    ) -> bool:
        """Check if actual value satisfies constraint"""
        if actual_value is None:
            return False
        
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
    
    def _generate_suggestion(
        self,
        part: Dict[str, Any],
        constraint_name: str,
        required: Any,
        actual: Any,
    ) -> Optional[NearMissSuggestion]:
        """
        Generate a near-miss suggestion.
        
        Args:
            part: Part data
            constraint_name: Failed constraint
            required: Required value
            actual: Actual value
        
        Returns:
            NearMissSuggestion or None
        """
        mpn = part.get('mpn')
        manufacturer = part.get('manufacturer')
        
        if not mpn or not manufacturer:
            return None
        
        # Calculate gap
        gap_size = self._calculate_gap(required, actual)
        
        # Generate human-readable suggestion
        suggestion_text = self._format_suggestion(
            constraint_name,
            required,
            actual,
            mpn,
        )
        
        return NearMissSuggestion(
            mpn=mpn,
            manufacturer=manufacturer,
            failed_constraint=constraint_name,
            required_value=required,
            actual_value=actual,
            gap_size=gap_size,
            suggestion=suggestion_text,
        )
    
    def _calculate_gap(
        self,
        required: Any,
        actual: Any,
    ) -> Optional[float]:
        """
        Calculate gap size (for sorting).
        
        Returns:
            Gap size (smaller = closer to requirement)
        """
        try:
            if isinstance(required, dict):
                # Range constraint
                if "min" in required:
                    req_val = required["min"]
                    if actual < req_val:
                        return float(req_val - actual)
                
                if "max" in required:
                    req_val = required["max"]
                    if actual > req_val:
                        return float(actual - req_val)
            
            elif isinstance(required, (int, float)) and isinstance(actual, (int, float)):
                return abs(float(required) - float(actual))
        
        except (TypeError, ValueError):
            pass
        
        return None
    
    def _format_suggestion(
        self,
        constraint_name: str,
        required: Any,
        actual: Any,
        mpn: str,
    ) -> str:
        """
        Format human-readable suggestion.
        
        Args:
            constraint_name: Failed constraint
            required: Required value
            actual: Actual value
            mpn: Part MPN
        
        Returns:
            Suggestion text
        """
        # Field-specific formatting
        field_formats = {
            'flash_kb': 'flash memory',
            'sram_kb': 'SRAM',
            'ram_kb': 'RAM',
            'can_count': 'CAN controllers',
            'can_fd_count': 'CAN-FD controllers',
            'uart_count': 'UART peripherals',
            'spi_count': 'SPI peripherals',
            'i2c_count': 'I2C peripherals',
            'temp_min_c': 'minimum temperature',
            'temp_max_c': 'maximum temperature',
            'package_family': 'package type',
            'pin_count': 'pin count',
        }
        
        field_label = field_formats.get(constraint_name, constraint_name)
        
        # Format based on constraint type
        if isinstance(required, dict):
            if "min" in required:
                req_val = required["min"]
                return (
                    f"Consider relaxing {field_label} requirement to ≥{actual} "
                    f"(from ≥{req_val}) to include {mpn}"
                )
            
            if "max" in required:
                req_val = required["max"]
                return (
                    f"Consider relaxing {field_label} requirement to ≤{actual} "
                    f"(from ≤{req_val}) to include {mpn}"
                )
        
        elif isinstance(required, list):
            return (
                f"Consider adding {actual} to acceptable {field_label} options "
                f"to include {mpn}"
            )
        
        else:
            return (
                f"Consider changing {field_label} from {required} to {actual} "
                f"to include {mpn}"
            )
