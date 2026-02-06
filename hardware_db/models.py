"""
Hardware Database Models

Data models for MCU and component specifications.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from enum import Enum


class CoreArchitecture(str, Enum):
    """MCU core architecture types"""
    ARM_CORTEX_M0 = "ARM Cortex-M0"
    ARM_CORTEX_M0_PLUS = "ARM Cortex-M0+"
    ARM_CORTEX_M3 = "ARM Cortex-M3"
    ARM_CORTEX_M4 = "ARM Cortex-M4"
    ARM_CORTEX_M7 = "ARM Cortex-M7"
    ARM_CORTEX_M33 = "ARM Cortex-M33"
    RISC_V = "RISC-V"
    XTENSA_LX6 = "Xtensa LX6"
    XTENSA_LX7 = "Xtensa LX7"
    AVR = "AVR"
    MSP430 = "MSP430"


class PackageType(str, Enum):
    """Package types"""
    QFN = "QFN"
    LQFP = "LQFP"
    TQFP = "TQFP"
    BGA = "BGA"
    WLCSP = "WLCSP"
    SOIC = "SOIC"
    DIP = "DIP"


class StockStatus(str, Enum):
    """Component availability status"""
    IN_STOCK = "in_stock"
    LIMITED = "limited"
    OBSOLETE = "obsolete"
    NRND = "not_recommended_for_new_designs"


@dataclass
class PowerConsumption:
    """Power consumption specifications"""
    active_ma: float  # Active mode current in mA
    standby_ua: float  # Standby mode current in µA
    sleep_ua: Optional[float] = None  # Sleep mode current in µA
    deep_sleep_ua: Optional[float] = None  # Deep sleep current in µA
    voltage_v: float = 3.3  # Operating voltage in V


@dataclass
class MCUSpec:
    """Complete MCU specification"""
    # Identification
    part_number: str
    manufacturer: str
    family: str  # e.g., "STM32F4", "ESP32", "nRF52"
    
    # Core specifications
    core_architecture: CoreArchitecture
    clock_mhz: int
    ram_kb: int
    flash_kb: int
    
    # Peripherals (list of available peripherals)
    peripherals: List[str] = field(default_factory=list)
    
    # Environmental specifications
    temp_range: Tuple[int, int] = (-40, 85)  # (min, max) in °C
    voltage_range: Tuple[float, float] = (1.8, 3.6)  # (min, max) in V
    
    # Package
    package: PackageType = PackageType.LQFP
    pin_count: int = 64
    
    # Cost and availability
    cost_usd: float = 0.0
    stock_status: StockStatus = StockStatus.IN_STOCK
    
    # Power consumption
    power_consumption: Optional[PowerConsumption] = None
    
    # Documentation
    datasheet_url: str = ""
    
    # Additional features
    has_fpu: bool = False
    has_dsp: bool = False
    has_crypto: bool = False
    has_wireless: bool = False  # WiFi, Bluetooth, etc.
    
    # Computed score (used during ranking)
    final_score: float = 0.0
    
    def satisfies_constraint(self, constraint_name: str, constraint_value: any) -> bool:
        """Check if this MCU satisfies a given constraint"""
        if constraint_name == "core_architecture":
            return self.core_architecture == constraint_value
        elif constraint_name == "ram_kb":
            if isinstance(constraint_value, dict):
                if "min" in constraint_value and self.ram_kb < constraint_value["min"]:
                    return False
                if "max" in constraint_value and self.ram_kb > constraint_value["max"]:
                    return False
                return True
            return self.ram_kb >= constraint_value
        elif constraint_name == "flash_kb":
            if isinstance(constraint_value, dict):
                if "min" in constraint_value and self.flash_kb < constraint_value["min"]:
                    return False
                if "max" in constraint_value and self.flash_kb > constraint_value["max"]:
                    return False
                return True
            return self.flash_kb >= constraint_value
        elif constraint_name == "peripherals":
            # All required peripherals must be present
            return all(p in self.peripherals for p in constraint_value)
        elif constraint_name == "cost_usd":
            if isinstance(constraint_value, dict):
                if "min" in constraint_value and self.cost_usd < constraint_value["min"]:
                    return False
                if "max" in constraint_value and self.cost_usd > constraint_value["max"]:
                    return False
                return True
            return self.cost_usd <= constraint_value
        elif constraint_name == "clock_mhz":
            if isinstance(constraint_value, dict):
                if "min" in constraint_value and self.clock_mhz < constraint_value["min"]:
                    return False
                if "max" in constraint_value and self.clock_mhz > constraint_value["max"]:
                    return False
                return True
            return self.clock_mhz >= constraint_value
        elif constraint_name == "has_fpu":
            return self.has_fpu == constraint_value
        elif constraint_name == "has_wireless":
            return self.has_wireless == constraint_value
        
        return True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "part_number": self.part_number,
            "manufacturer": self.manufacturer,
            "family": self.family,
            "core_architecture": self.core_architecture.value if isinstance(self.core_architecture, Enum) else self.core_architecture,
            "clock_mhz": self.clock_mhz,
            "ram_kb": self.ram_kb,
            "flash_kb": self.flash_kb,
            "peripherals": self.peripherals,
            "temp_range": self.temp_range,
            "voltage_range": self.voltage_range,
            "package": self.package.value if isinstance(self.package, Enum) else self.package,
            "pin_count": self.pin_count,
            "cost_usd": self.cost_usd,
            "stock_status": self.stock_status.value if isinstance(self.stock_status, Enum) else self.stock_status,
            "power_consumption": {
                "active_ma": self.power_consumption.active_ma,
                "standby_ua": self.power_consumption.standby_ua,
                "sleep_ua": self.power_consumption.sleep_ua,
                "deep_sleep_ua": self.power_consumption.deep_sleep_ua,
                "voltage_v": self.power_consumption.voltage_v
            } if self.power_consumption else None,
            "datasheet_url": self.datasheet_url,
            "has_fpu": self.has_fpu,
            "has_dsp": self.has_dsp,
            "has_crypto": self.has_crypto,
            "has_wireless": self.has_wireless
        }


@dataclass
class Constraint:
    """Represents a single constraint"""
    name: str
    value: any
    is_hard: bool = True  # Hard constraint (MUST satisfy) vs soft (NICE to have)
    weight: float = 1.0  # Weight for soft constraints


@dataclass
class FilterRequest:
    """Request for filtering MCUs"""
    hard_constraints: Dict[str, any] = field(default_factory=dict)
    soft_constraints: Dict[str, any] = field(default_factory=dict)
    optimization_goal: str = "balanced"  # cost, power, performance, balanced
    max_results: int = 10
