"""
Multi-Criteria Ranking

Ranking algorithm for MCU selection based on multiple optimization criteria.
Previously imported MCUSpec from the non-existent hardware_db.models;
now imports from the local parametric_filter module.
"""

from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .parametric_filter import MCUSpec


def multi_criteria_rank(
    candidates: List[Tuple["MCUSpec", float]],
    goal: str = "balanced",
) -> List[Tuple["MCUSpec", float]]:
    """
    Rank MCUs using multi-criteria optimisation.

    This is a DETERMINISTIC function with stable sorting.

    Args:
        candidates: List of (MCU, soft_score) tuples
        goal: Optimisation goal — "cost", "power", "performance", or "balanced"

    Returns:
        Sorted list of (MCU, final_score) tuples (highest score first)
    """
    if not candidates:
        return []

    weights = {
        "cost":        {"cost": 0.70, "power": 0.10, "performance": 0.20},
        "power":       {"cost": 0.20, "power": 0.60, "performance": 0.20},
        "performance": {"cost": 0.10, "power": 0.10, "performance": 0.80},
        "balanced":    {"cost": 0.33, "power": 0.33, "performance": 0.34},
    }
    w = weights.get(goal, weights["balanced"])

    cost_scores = normalize_cost([mcu.cost_usd            for mcu, _ in candidates])
    power_scores = normalize_power([_get_power_metric(mcu) for mcu, _ in candidates])
    perf_scores  = normalize_performance([mcu.clock_mhz   for mcu, _ in candidates])

    ranked: List[Tuple["MCUSpec", float]] = []
    for i, (mcu, soft_score) in enumerate(candidates):
        final_score = (
            w["cost"]        * cost_scores[i]  +
            w["power"]       * power_scores[i] +
            w["performance"] * perf_scores[i]  +
            0.10             * soft_score
        )
        mcu.final_score = final_score
        ranked.append((mcu, final_score))

    # Stable sort: descending score, then ascending part_number for determinism
    ranked.sort(key=lambda x: (-x[1], x[0].part_number))
    return ranked


# ---------------------------------------------------------------------------
# Normalisation helpers — all guard against zero-range (all-equal) inputs
# ---------------------------------------------------------------------------

def normalize_cost(costs: List[float]) -> List[float]:
    """Lower cost → higher score (0–1)."""
    if not costs or all(c == 0 for c in costs):
        return [1.0] * len(costs)
    mn, mx = min(costs), max(costs)
    if mn == mx:
        return [1.0] * len(costs)
    return [(mx - c) / (mx - mn) for c in costs]


def normalize_power(power_values: List[float]) -> List[float]:
    """Lower power → higher score (0–1)."""
    if not power_values or all(p == 0 for p in power_values):
        return [1.0] * len(power_values)
    mn, mx = min(power_values), max(power_values)
    if mn == mx:
        return [1.0] * len(power_values)
    return [(mx - p) / (mx - mn) for p in power_values]


def normalize_performance(perf_values: List[float]) -> List[float]:
    """Higher performance → higher score (0–1)."""
    if not perf_values or all(p == 0 for p in perf_values):
        return [1.0] * len(perf_values)
    mn, mx = min(perf_values), max(perf_values)
    if mn == mx:
        return [1.0] * len(perf_values)
    return [(p - mn) / (mx - mn) for p in perf_values]


def _get_power_metric(mcu: "MCUSpec") -> float:
    """Composite power metric. Returns 100 mA if no data available."""
    if not mcu.power_consumption:
        return 100.0
    active_ma   = mcu.power_consumption.active_ma
    standby_ma  = mcu.power_consumption.standby_ua / 1000.0
    return 0.7 * active_ma + 0.3 * standby_ma


# ---------------------------------------------------------------------------
# Convenience ranking functions
# ---------------------------------------------------------------------------

def calculate_value_score(mcu: "MCUSpec") -> float:
    """Performance per dollar; higher is better."""
    if mcu.cost_usd == 0:
        return 0.0
    return (mcu.ram_kb + mcu.flash_kb + mcu.clock_mhz) / mcu.cost_usd


def rank_by_value(candidates: List["MCUSpec"]) -> List["MCUSpec"]:
    """Rank MCUs by value (performance per dollar)."""
    scored = [(mcu, calculate_value_score(mcu)) for mcu in candidates]
    scored.sort(key=lambda x: (-x[1], x[0].part_number))
    return [mcu for mcu, _ in scored]


def rank_by_power_efficiency(candidates: List["MCUSpec"]) -> List["MCUSpec"]:
    """Rank MCUs by power efficiency (performance per watt)."""
    scored = []
    for mcu in candidates:
        if mcu.power_consumption:
            efficiency = mcu.clock_mhz / (mcu.power_consumption.active_ma + 0.1)
        else:
            efficiency = 0.0
        scored.append((mcu, efficiency))
    scored.sort(key=lambda x: (-x[1], x[0].part_number))
    return [mcu for mcu, _ in scored]
