"""
Constraint Parser

Parse natural language requirements into structured constraints.
"""

import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Local models — previously imported from the non-existent hardware_db.models.
# These mirror the legacy FilterRequest/CoreArchitecture API so that callers
# of this module continue to work unchanged.
# ---------------------------------------------------------------------------

class CoreArchitecture(str, Enum):
    ARM_CORTEX_M0      = "Cortex-M0"
    ARM_CORTEX_M0_PLUS = "Cortex-M0+"
    ARM_CORTEX_M3      = "Cortex-M3"
    ARM_CORTEX_M4      = "Cortex-M4"
    ARM_CORTEX_M7      = "Cortex-M7"
    ARM_CORTEX_M33     = "Cortex-M33"
    RISC_V             = "RISC-V"
    XTENSA_LX6         = "Xtensa LX6"
    XTENSA_LX7         = "Xtensa LX7"


@dataclass
class FilterRequest:
    hard_constraints:  Dict = field(default_factory=dict)
    soft_constraints:  Dict = field(default_factory=dict)
    optimization_goal: str  = "balanced"
    max_results:       int  = 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_requirements(text: str) -> FilterRequest:
    """
    Parse natural language requirements into structured constraints.

    Args:
        text: Natural language requirement description

    Returns:
        FilterRequest with parsed constraints
    """
    text_lower = text.lower()
    hard_constraints: Dict = {}
    soft_constraints: Dict = {}
    optimization_goal = "balanced"

    # Parse core architecture
    core_arch = parse_core_architecture(text_lower)
    if core_arch:
        hard_constraints["core_architecture"] = core_arch

    # Parse RAM requirement
    ram_kb = parse_memory_requirement(text_lower, ["ram", "sram"])
    if ram_kb:
        hard_constraints["ram_kb"] = ram_kb

    # Parse Flash requirement
    flash_kb = parse_memory_requirement(text_lower, ["flash", "rom"])
    if flash_kb:
        hard_constraints["flash_kb"] = flash_kb

    # Parse peripherals
    peripherals = parse_peripherals(text_lower)
    if peripherals:
        hard_constraints["peripherals"] = peripherals

    # Parse cost constraint
    cost = parse_cost(text_lower)
    if cost:
        hard_constraints["cost_usd"] = cost

    # Parse clock speed
    clock = parse_clock_speed(text_lower)
    if clock:
        hard_constraints["clock_mhz"] = clock

    # Detect optimization goal
    if any(kw in text_lower for kw in ["low power", "battery", "power efficient", "low-power"]):
        optimization_goal = "power"
    elif any(kw in text_lower for kw in ["cheap", "cost", "budget", "affordable"]):
        optimization_goal = "cost"
    elif any(kw in text_lower for kw in ["fast", "performance", "high-speed", "powerful"]):
        optimization_goal = "performance"

    # Detect FPU requirement
    if "fpu" in text_lower or "floating point" in text_lower:
        hard_constraints["has_fpu"] = True

    # Detect wireless requirement
    if any(kw in text_lower for kw in ["wifi", "bluetooth", "wireless", "ble"]):
        hard_constraints["has_wireless"] = True

    return FilterRequest(
        hard_constraints=hard_constraints,
        soft_constraints=soft_constraints,
        optimization_goal=optimization_goal,
        max_results=10,
    )


def parse_core_architecture(text: str) -> Optional[str]:
    """Parse core architecture from text"""
    arch_patterns = {
        CoreArchitecture.ARM_CORTEX_M0:      ["cortex-m0", "cortex m0", "arm m0"],
        CoreArchitecture.ARM_CORTEX_M0_PLUS: ["cortex-m0+", "cortex m0+", "cortex-m0 plus"],
        CoreArchitecture.ARM_CORTEX_M3:      ["cortex-m3", "cortex m3", "arm m3"],
        CoreArchitecture.ARM_CORTEX_M4:      ["cortex-m4", "cortex m4", "arm m4"],
        CoreArchitecture.ARM_CORTEX_M7:      ["cortex-m7", "cortex m7", "arm m7"],
        CoreArchitecture.ARM_CORTEX_M33:     ["cortex-m33", "cortex m33", "arm m33"],
        CoreArchitecture.RISC_V:             ["risc-v", "risc v", "riscv"],
        CoreArchitecture.XTENSA_LX6:         ["xtensa lx6", "lx6"],
        CoreArchitecture.XTENSA_LX7:         ["xtensa lx7", "lx7"],
    }

    for arch, patterns in arch_patterns.items():
        if any(pattern in text for pattern in patterns):
            return arch.value

    return None


def parse_memory_requirement(text: str, keywords: List[str]) -> Optional[Dict]:
    """Parse memory (RAM/Flash) requirement from text"""
    for keyword in keywords:
        # Pattern: "at least 128KB RAM" or "128KB+ RAM" or ">=128KB RAM"
        pattern = rf"(?:at least|>=|≥|\+)\s*(\d+)\s*(?:kb|k)?\s*{keyword}"
        match = re.search(pattern, text)
        if match:
            return {"min": int(match.group(1))}

        # Pattern: "128KB RAM" (assume minimum)
        pattern = rf"(\d+)\s*(?:kb|k)?\s*{keyword}"
        match = re.search(pattern, text)
        if match:
            return {"min": int(match.group(1))}

    return None


def parse_peripherals(text: str) -> List[str]:
    """Parse required peripherals from text"""
    peripheral_keywords = {
        "UART":      ["uart", "serial"],
        "SPI":       ["spi"],
        "I2C":       ["i2c", "i²c", "iic"],
        "USB":       ["usb"],
        "CAN":       ["can", "can bus"],
        "ETHERNET":  ["ethernet", "eth"],
        "ADC":       ["adc", "analog"],
        "DAC":       ["dac"],
        "PWM":       ["pwm"],
        "TIMER":     ["timer"],
        "DMA":       ["dma"],
        "WIFI":      ["wifi", "wi-fi"],
        "BLUETOOTH": ["bluetooth", "ble", "bt"],
    }

    found: List[str] = []
    for peripheral, kws in peripheral_keywords.items():
        if any(kw in text for kw in kws):
            found.append(peripheral)

    return found


def parse_cost(text: str) -> Optional[Dict]:
    """Parse cost constraint from text"""
    pattern = r"(?:under|<|less than|cheaper than)\s*\$?\s*(\d+(?:\.\d+)?)"
    match = re.search(pattern, text)
    if match:
        return {"max": float(match.group(1))}

    pattern = r"(?:costs?|price)\s*\$?\s*(\d+(?:\.\d+)?)"
    match = re.search(pattern, text)
    if match:
        return {"max": float(match.group(1))}

    return None


def parse_clock_speed(text: str) -> Optional[Dict]:
    """Parse clock speed requirement from text"""
    pattern = r"(?:at least|>=|≥)\s*(\d+)\s*(?:mhz)"
    match = re.search(pattern, text)
    if match:
        return {"min": int(match.group(1))}

    return None


def format_constraints_for_display(request: FilterRequest) -> str:
    """Format constraints in a human-readable way"""
    lines = []

    if request.hard_constraints:
        lines.append("Hard Constraints (MUST satisfy):")
        for name, value in request.hard_constraints.items():
            lines.append(f"  - {name}: {format_constraint_value(value)}")

    if request.soft_constraints:
        lines.append("\nSoft Constraints (NICE to have):")
        for name, value in request.soft_constraints.items():
            lines.append(f"  - {name}: {format_constraint_value(value)}")

    lines.append(f"\nOptimization Goal: {request.optimization_goal}")

    return "\n".join(lines)


def format_constraint_value(value) -> str:
    """Format a constraint value for display"""
    if isinstance(value, dict):
        parts = []
        if "min" in value:
            parts.append(f"≥ {value['min']}")
        if "max" in value:
            parts.append(f"≤ {value['max']}")
        return " and ".join(parts)
    elif isinstance(value, list):
        return ", ".join(str(v) for v in value)
    else:
        return str(value)
