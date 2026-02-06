"""
Parametric Filter

Deterministic filtering engine for MCU selection based on constraints.
"""

from typing import List, Dict, Tuple
from hardware_db.models import MCUSpec, FilterRequest


def filter_mcus(request: FilterRequest, database: List[MCUSpec]) -> List[Tuple[MCUSpec, float]]:
    """
    Filter MCUs based on constraints and return ranked results.
    
    This is a DETERMINISTIC function - same input always produces same output.
    
    Args:
        request: FilterRequest with hard/soft constraints and optimization goal
        database: List of all available MCUs
    
    Returns:
        List of (MCU, score) tuples, sorted by score (highest first)
    """
    # Step 1: Hard constraint filtering (MUST satisfy)
    candidates = []
    for mcu in database:
        if satisfies_all_hard_constraints(mcu, request.hard_constraints):
            candidates.append(mcu)
    
    if not candidates:
        return []  # No MCUs satisfy hard constraints
    
    # Step 2: Soft constraint scoring (NICE to have)
    scored = []
    for mcu in candidates:
        soft_score = calculate_soft_score(mcu, request.soft_constraints)
        scored.append((mcu, soft_score))
    
    # Step 3: Multi-criteria ranking
    from .ranking import multi_criteria_rank
    ranked = multi_criteria_rank(scored, request.optimization_goal)
    
    # Step 4: Return top N results
    return ranked[:request.max_results]


def satisfies_all_hard_constraints(mcu: MCUSpec, hard_constraints: Dict) -> bool:
    """
    Check if MCU satisfies ALL hard constraints.
    
    Args:
        mcu: MCU specification
        hard_constraints: Dictionary of constraint_name -> constraint_value
    
    Returns:
        True if all hard constraints are satisfied, False otherwise
    """
    for constraint_name, constraint_value in hard_constraints.items():
        if not mcu.satisfies_constraint(constraint_name, constraint_value):
            return False
    return True


def calculate_soft_score(mcu: MCUSpec, soft_constraints: Dict) -> float:
    """
    Calculate score for soft constraints (0.0 to 1.0).
    
    Soft constraints are weighted preferences, not requirements.
    
    Args:
        mcu: MCU specification
        soft_constraints: Dictionary of constraint_name -> (constraint_value, weight)
    
    Returns:
        Normalized score between 0.0 and 1.0
    """
    if not soft_constraints:
        return 1.0  # No soft constraints, perfect score
    
    total_weight = 0.0
    weighted_score = 0.0
    
    for constraint_name, constraint_data in soft_constraints.items():
        if isinstance(constraint_data, dict) and "value" in constraint_data:
            constraint_value = constraint_data["value"]
            weight = constraint_data.get("weight", 1.0)
        else:
            constraint_value = constraint_data
            weight = 1.0
        
        total_weight += weight
        
        # Check if constraint is satisfied
        if mcu.satisfies_constraint(constraint_name, constraint_value):
            weighted_score += weight
    
    return weighted_score / total_weight if total_weight > 0 else 1.0


def filter_by_price_range(database: List[MCUSpec], min_price: float = 0.0, max_price: float = float('inf')) -> List[MCUSpec]:
    """Filter MCUs by price range"""
    return [mcu for mcu in database if min_price <= mcu.cost_usd <= max_price]


def filter_by_core_architecture(database: List[MCUSpec], architecture: str) -> List[MCUSpec]:
    """Filter MCUs by core architecture"""
    return [mcu for mcu in database if mcu.core_architecture.value == architecture or mcu.core_architecture == architecture]


def filter_by_ram(database: List[MCUSpec], min_ram_kb: int) -> List[MCUSpec]:
    """Filter MCUs by minimum RAM"""
    return [mcu for mcu in database if mcu.ram_kb >= min_ram_kb]


def filter_by_flash(database: List[MCUSpec], min_flash_kb: int) -> List[MCUSpec]:
    """Filter MCUs by minimum Flash"""
    return [mcu for mcu in database if mcu.flash_kb >= min_flash_kb]


def filter_by_peripherals(database: List[MCUSpec], required_peripherals: List[str]) -> List[MCUSpec]:
    """Filter MCUs that have ALL required peripherals"""
    return [
        mcu for mcu in database
        if all(peripheral.upper() in [p.upper() for p in mcu.peripherals] for peripheral in required_peripherals)
    ]


def filter_by_manufacturer(database: List[MCUSpec], manufacturer: str) -> List[MCUSpec]:
    """Filter MCUs by manufacturer"""
    return [mcu for mcu in database if mcu.manufacturer.lower() == manufacturer.lower()]


def get_unique_values(database: List[MCUSpec], field: str) -> List:
    """Get unique values for a specific field across all MCUs"""
    values = set()
    for mcu in database:
        value = getattr(mcu, field, None)
        if value is not None:
            if isinstance(value, list):
                values.update(value)
            else:
                values.add(value)
    return sorted(list(values))
