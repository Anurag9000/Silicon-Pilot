"""
Parametric Filter

Deterministic filtering engine for MCU selection based on constraints.
Previously imported MCUSpec/FilterRequest from the non-existent hardware_db.models.
Now uses local dataclass stubs that are compatible with the same interface.
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Local stub models (previously from hardware_db.models)
# ---------------------------------------------------------------------------

@dataclass
class PowerConsumption:
    active_ma:   float = 0.0
    standby_ua:  float = 0.0


@dataclass
class MCUSpec:
    """Lightweight MCU specification used by the parametric filter."""
    part_number:      str
    manufacturer:     str
    core_architecture: str
    clock_mhz:        float
    ram_kb:           float
    flash_kb:         float
    cost_usd:         float          = 0.0
    peripherals:      List[str]      = field(default_factory=list)
    power_consumption: Optional[PowerConsumption] = None
    final_score:      float          = 0.0
    extras:           Dict[str, Any] = field(default_factory=dict)

    def satisfies_constraint(self, name: str, value: Any) -> bool:
        """Return True if this MCU satisfies the given constraint."""
        # Range constraint: {"min": X} or {"max": Y} or both
        if isinstance(value, dict):
            field_map = {
                "ram_kb":       self.ram_kb,
                "flash_kb":     self.flash_kb,
                "clock_mhz":    self.clock_mhz,
                "cost_usd":     self.cost_usd,
                "core_architecture": self.core_architecture,
            }
            actual = field_map.get(name)
            if actual is None:
                return True   # unknown field: pass through
            mn = value.get("min")
            mx = value.get("max")
            if mn is not None and actual < mn:
                return False
            if mx is not None and actual > mx:
                return False
            return True

        # Boolean / equality constraint
        attr = getattr(self, name, None)
        if attr is None:
            return True
        return attr == value


# ---------------------------------------------------------------------------
# Public filter API
# ---------------------------------------------------------------------------

def filter_mcus(request, database: List[MCUSpec]) -> List[Tuple[MCUSpec, float]]:
    """
    Filter MCUs based on constraints and return ranked results.

    This is a DETERMINISTIC function — same input always produces same output.

    Args:
        request: FilterRequest with hard/soft constraints and optimization goal
        database: List of all available MCUs

    Returns:
        List of (MCU, score) tuples, sorted by score (highest first)
    """
    # Step 1: Hard constraint filtering
    candidates = [
        mcu for mcu in database
        if satisfies_all_hard_constraints(mcu, request.hard_constraints)
    ]

    if not candidates:
        return []

    # Step 2: Soft constraint scoring
    scored = [(mcu, calculate_soft_score(mcu, request.soft_constraints)) for mcu in candidates]

    # Step 3: Multi-criteria ranking
    from .ranking import multi_criteria_rank
    ranked = multi_criteria_rank(scored, request.optimization_goal)

    # Step 4: Top N
    return ranked[:request.max_results]


def satisfies_all_hard_constraints(mcu: MCUSpec, hard_constraints: Dict) -> bool:
    for name, value in hard_constraints.items():
        if not mcu.satisfies_constraint(name, value):
            return False
    return True


def calculate_soft_score(mcu: MCUSpec, soft_constraints: Dict) -> float:
    if not soft_constraints:
        return 1.0

    total_weight   = 0.0
    weighted_score = 0.0

    for name, data in soft_constraints.items():
        if isinstance(data, dict) and "value" in data:
            value  = data["value"]
            weight = data.get("weight", 1.0)
        else:
            value  = data
            weight = 1.0

        total_weight += weight
        if mcu.satisfies_constraint(name, value):
            weighted_score += weight

    return weighted_score / total_weight if total_weight > 0 else 1.0


def filter_by_price_range(database: List[MCUSpec], min_price: float = 0.0, max_price: float = float("inf")) -> List[MCUSpec]:
    return [mcu for mcu in database if min_price <= mcu.cost_usd <= max_price]


def filter_by_core_architecture(database: List[MCUSpec], architecture: str) -> List[MCUSpec]:
    return [mcu for mcu in database if mcu.core_architecture == architecture]


def filter_by_ram(database: List[MCUSpec], min_ram_kb: int) -> List[MCUSpec]:
    return [mcu for mcu in database if mcu.ram_kb >= min_ram_kb]


def filter_by_flash(database: List[MCUSpec], min_flash_kb: int) -> List[MCUSpec]:
    return [mcu for mcu in database if mcu.flash_kb >= min_flash_kb]


def filter_by_peripherals(database: List[MCUSpec], required_peripherals: List[str]) -> List[MCUSpec]:
    return [
        mcu for mcu in database
        if all(p.upper() in [x.upper() for x in mcu.peripherals] for p in required_peripherals)
    ]


def filter_by_manufacturer(database: List[MCUSpec], manufacturer: str) -> List[MCUSpec]:
    return [mcu for mcu in database if mcu.manufacturer.lower() == manufacturer.lower()]


def get_unique_values(database: List[MCUSpec], field_name: str) -> List:
    values: set = set()
    for mcu in database:
        value = getattr(mcu, field_name, None)
        if value is not None:
            if isinstance(value, list):
                values.update(value)
            else:
                values.add(value)
    return sorted(list(values))
