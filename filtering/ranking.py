"""
Multi-Criteria Ranking

Ranking algorithm for MCU selection based on multiple optimization criteria.
"""

from typing import List, Tuple
from hardware_db.models import MCUSpec


def multi_criteria_rank(candidates: List[Tuple[MCUSpec, float]], goal: str = "balanced") -> List[Tuple[MCUSpec, float]]:
    """
    Rank MCUs using multi-criteria optimization.
    
    This is a DETERMINISTIC function with stable sorting.
    
    Args:
        candidates: List of (MCU, soft_score) tuples
        goal: Optimization goal - "cost", "power", "performance", or "balanced"
    
    Returns:
        Sorted list of (MCU, final_score) tuples (highest score first)
    """
    if not candidates:
        return []
    
    # Define weights for each optimization goal
    weights = {
        "cost": {"cost": 0.7, "power": 0.1, "performance": 0.2},
        "power": {"cost": 0.2, "power": 0.6, "performance": 0.2},
        "performance": {"cost": 0.1, "power": 0.1, "performance": 0.8},
        "balanced": {"cost": 0.33, "power": 0.33, "performance": 0.34}
    }
    
    w = weights.get(goal, weights["balanced"])
    
    # Normalize metrics across all candidates
    cost_scores = normalize_cost([mcu.cost_usd for mcu, _ in candidates])
    power_scores = normalize_power([get_power_metric(mcu) for mcu, _ in candidates])
    perf_scores = normalize_performance([mcu.clock_mhz for mcu, _ in candidates])
    
    # Calculate final scores
    ranked = []
    for i, (mcu, soft_score) in enumerate(candidates):
        final_score = (
            w["cost"] * cost_scores[i] +
            w["power"] * power_scores[i] +
            w["performance"] * perf_scores[i] +
            0.1 * soft_score  # Soft constraints contribute 10%
        )
        mcu.final_score = final_score
        ranked.append((mcu, final_score))
    
    # Stable sort by score (descending), then by part_number (for determinism)
    ranked.sort(key=lambda x: (-x[1], x[0].part_number))
    
    return ranked


def normalize_cost(costs: List[float]) -> List[float]:
    """
    Normalize cost scores (lower cost = higher score).
    
    Returns scores between 0.0 and 1.0.
    """
    if not costs or all(c == 0 for c in costs):
        return [1.0] * len(costs)
    
    min_cost = min(costs)
    max_cost = max(costs)
    
    if min_cost == max_cost:
        return [1.0] * len(costs)
    
    # Invert: lower cost gets higher score
    return [(max_cost - c) / (max_cost - min_cost) for c in costs]


def normalize_power(power_values: List[float]) -> List[float]:
    """
    Normalize power consumption scores (lower power = higher score).
    
    Returns scores between 0.0 and 1.0.
    """
    if not power_values or all(p == 0 for p in power_values):
        return [1.0] * len(power_values)
    
    min_power = min(power_values)
    max_power = max(power_values)
    
    if min_power == max_power:
        return [1.0] * len(power_values)
    
    # Invert: lower power gets higher score
    return [(max_power - p) / (max_power - min_power) for p in power_values]


def normalize_performance(perf_values: List[float]) -> List[float]:
    """
    Normalize performance scores (higher performance = higher score).
    
    Returns scores between 0.0 and 1.0.
    """
    if not perf_values or all(p == 0 for p in perf_values):
        return [1.0] * len(perf_values)
    
    min_perf = min(perf_values)
    max_perf = max(perf_values)
    
    if min_perf == max_perf:
        return [1.0] * len(perf_values)
    
    # Direct: higher performance gets higher score
    return [(p - min_perf) / (max_perf - min_perf) for p in perf_values]


def get_power_metric(mcu: MCUSpec) -> float:
    """
    Calculate a composite power consumption metric.
    
    Combines active and standby power with weighting.
    """
    if not mcu.power_consumption:
        return 100.0  # Default high value if no power data
    
    # Weight active power more heavily (70%) than standby (30%)
    active_ma = mcu.power_consumption.active_ma
    standby_ua = mcu.power_consumption.standby_ua / 1000.0  # Convert to mA
    
    return 0.7 * active_ma + 0.3 * standby_ua


def calculate_value_score(mcu: MCUSpec) -> float:
    """
    Calculate value score (performance per dollar).
    
    Higher is better.
    """
    if mcu.cost_usd == 0:
        return 0.0
    
    # Simple metric: (RAM + Flash + Clock) / Cost
    value = (mcu.ram_kb + mcu.flash_kb + mcu.clock_mhz) / mcu.cost_usd
    return value


def rank_by_value(candidates: List[MCUSpec]) -> List[MCUSpec]:
    """Rank MCUs by value (performance per dollar)"""
    scored = [(mcu, calculate_value_score(mcu)) for mcu in candidates]
    scored.sort(key=lambda x: (-x[1], x[0].part_number))  # Stable sort
    return [mcu for mcu, _ in scored]


def rank_by_power_efficiency(candidates: List[MCUSpec]) -> List[MCUSpec]:
    """Rank MCUs by power efficiency (performance per watt)"""
    scored = []
    for mcu in candidates:
        if mcu.power_consumption:
            # Performance / Power
            efficiency = mcu.clock_mhz / (mcu.power_consumption.active_ma + 0.1)
            scored.append((mcu, efficiency))
        else:
            scored.append((mcu, 0.0))
    
    scored.sort(key=lambda x: (-x[1], x[0].part_number))  # Stable sort
    return [mcu for mcu, _ in scored]
