"""
Design Ontology for Silicon-Pilot Phase 2

Defines the formal vocabulary for device types, subsystems, functions,
interfaces, and environmental contexts used in template-based architecture synthesis.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Set, Any
from pydantic import BaseModel, Field


# ============================================================================
# Device Types
# ============================================================================

class DeviceType(str, Enum):
    """High-level device categories"""
    SENSOR_NODE = "sensor_node"
    MOTOR_CONTROLLER = "motor_controller"
    GATEWAY = "gateway"
    DATA_LOGGER = "data_logger"
    WEARABLE = "wearable"
    SMART_APPLIANCE = "smart_appliance"
    ROBOTICS_CONTROLLER = "robotics_controller"
    POWER_SUPPLY = "power_supply"
    DISPLAY_CONTROLLER = "display_controller"
    AUDIO_DEVICE = "audio_device"
    EDGE_AI_CAMERA = "edge_ai_camera"
    INDUSTRIAL_CONTROLLER = "industrial_controller"


# ============================================================================
# Subsystems
# ============================================================================

class SubsystemType(str, Enum):
    """Major subsystem categories"""
    COMPUTE = "compute"
    POWER = "power"
    COMMUNICATION = "communication"
    SENSING = "sensing"
    ACTUATION = "actuation"
    STORAGE = "storage"
    DISPLAY = "display"
    AUDIO = "audio"
    PROTECTION = "protection"
    DEBUG_PROGRAMMING = "debug_programming"
    USER_INTERFACE = "user_interface"


# ============================================================================
# Functions
# ============================================================================

class ComputeFunction(str, Enum):
    """Compute subsystem functions"""
    MOTOR_CONTROL = "motor_control"
    DATA_ACQUISITION = "data_acquisition"
    SIGNAL_PROCESSING = "signal_processing"
    EDGE_AI = "edge_ai"
    PROTOCOL_HANDLING = "protocol_handling"
    STATE_MACHINE = "state_machine"
    PID_CONTROL = "pid_control"
    FFT_PROCESSING = "fft_processing"


class PowerFunction(str, Enum):
    """Power subsystem functions"""
    BUCK_CONVERSION = "buck_conversion"
    BOOST_CONVERSION = "boost_conversion"
    LINEAR_REGULATION = "linear_regulation"
    BATTERY_MANAGEMENT = "battery_management"
    POWER_MONITORING = "power_monitoring"
    LOAD_SWITCHING = "load_switching"


class CommunicationFunction(str, Enum):
    """Communication subsystem functions"""
    WIRELESS_UPLINK = "wireless_uplink"
    WIRED_INTERFACE = "wired_interface"
    LOCAL_NETWORK = "local_network"
    LONG_RANGE_COMM = "long_range_comm"
    SHORT_RANGE_COMM = "short_range_comm"


# ============================================================================
# Interfaces
# ============================================================================

class InterfaceType(str, Enum):
    """Communication interface types"""
    # Serial
    UART = "uart"
    SPI = "spi"
    I2C = "i2c"
    
    # Automotive/Industrial
    CAN = "can"
    CAN_FD = "can_fd"
    LIN = "lin"
    RS485 = "rs485"
    RS232 = "rs232"
    
    # USB
    USB_FS = "usb_fs"
    USB_HS = "usb_hs"
    USB_OTG = "usb_otg"
    
    # Ethernet
    ETHERNET = "ethernet"
    ETHERNET_10_100 = "ethernet_10_100"
    ETHERNET_GIGABIT = "ethernet_gigabit"
    
    # Wireless
    WIFI = "wifi"
    BLUETOOTH = "bluetooth"
    BLE = "ble"
    ZIGBEE = "zigbee"
    LORA = "lora"
    LORAWAN = "lorawan"
    CELLULAR = "cellular"
    NFC = "nfc"
    
    # Storage
    SDMMC = "sdmmc"
    EMMC = "emmc"
    
    # Display
    PARALLEL_RGB = "parallel_rgb"
    MIPI_DSI = "mipi_dsi"
    LVDS = "lvds"
    
    # Audio
    I2S = "i2s"
    SAI = "sai"
    
    # Debug
    JTAG = "jtag"
    SWD = "swd"


# ============================================================================
# Environmental Contexts
# ============================================================================

class EnvironmentType(str, Enum):
    """Operating environment categories"""
    INDOOR_CONTROLLED = "indoor_controlled"
    INDOOR_UNCONTROLLED = "indoor_uncontrolled"
    OUTDOOR = "outdoor"
    AUTOMOTIVE = "automotive"
    INDUSTRIAL = "industrial"
    MEDICAL = "medical"
    AEROSPACE = "aerospace"
    MARINE = "marine"
    HARSH = "harsh"


class TemperatureGrade(str, Enum):
    """Standard temperature grades"""
    COMMERCIAL = "commercial"  # 0 to 70°C
    INDUSTRIAL = "industrial"  # -40 to 85°C
    EXTENDED = "extended"      # -40 to 105°C
    AUTOMOTIVE = "automotive"  # -40 to 125°C
    MILITARY = "military"      # -55 to 125°C


# ============================================================================
# Performance Dimensions
# ============================================================================

class PowerProfile(str, Enum):
    """Power consumption profiles"""
    ULTRA_LOW_POWER = "ultra_low_power"  # <1mA active, <1µA sleep
    LOW_POWER = "low_power"              # 1-10mA active, <10µA sleep
    MODERATE_POWER = "moderate_power"    # 10-100mA active
    HIGH_POWER = "high_power"            # >100mA active


class PerformanceClass(str, Enum):
    """Processing performance classes"""
    LOW_END = "low_end"          # <50 MHz, basic control
    MID_RANGE = "mid_range"      # 50-200 MHz, moderate processing
    HIGH_PERFORMANCE = "high_performance"  # 200-500 MHz, DSP/AI
    ULTRA_HIGH = "ultra_high"    # >500 MHz, complex processing


# ============================================================================
# Pydantic Models
# ============================================================================

class Subsystem(BaseModel):
    """Represents a subsystem in the architecture"""
    type: SubsystemType
    required_functions: List[str] = Field(default_factory=list)
    baseline_constraints: Dict[str, Any] = Field(default_factory=dict)
    recommended_parts: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class Interface(BaseModel):
    """Represents a communication interface"""
    type: InterfaceType
    required: bool = True
    count: int = 1
    specifications: Dict[str, Any] = Field(default_factory=dict)


class EnvironmentalRequirements(BaseModel):
    """Environmental operating requirements"""
    environment_type: EnvironmentType
    temperature_grade: TemperatureGrade
    temp_min_c: int = -40
    temp_max_c: int = 85
    humidity_max_percent: Optional[int] = None
    vibration_resistance: bool = False
    ip_rating: Optional[str] = None  # e.g., "IP67"


class PerformanceRequirements(BaseModel):
    """Performance and power requirements"""
    power_profile: PowerProfile
    performance_class: PerformanceClass
    battery_powered: bool = False
    battery_life_hours: Optional[int] = None
    max_power_consumption_mw: Optional[int] = None


class ArchitectureGraph(BaseModel):
    """Complete architecture graph for a device"""
    device_type: DeviceType
    description: str
    subsystems: Dict[str, Subsystem] = Field(default_factory=dict)
    interfaces: List[Interface] = Field(default_factory=list)
    environmental_requirements: Optional[EnvironmentalRequirements] = None
    performance_requirements: Optional[PerformanceRequirements] = None
    additional_constraints: Dict[str, Any] = Field(default_factory=dict)
    
    def add_subsystem(self, name: str, subsystem: Subsystem):
        """Add a subsystem to the architecture"""
        self.subsystems[name] = subsystem
    
    def add_interface(self, interface: Interface):
        """Add an interface requirement"""
        self.interfaces.append(interface)
    
    def get_all_required_interfaces(self) -> Set[InterfaceType]:
        """Get set of all required interface types"""
        return {iface.type for iface in self.interfaces if iface.required}


# ============================================================================
# Helper Functions
# ============================================================================

def get_temperature_range(grade: TemperatureGrade) -> tuple[int, int]:
    """Get temperature range for a grade"""
    ranges = {
        TemperatureGrade.COMMERCIAL: (0, 70),
        TemperatureGrade.INDUSTRIAL: (-40, 85),
        TemperatureGrade.EXTENDED: (-40, 105),
        TemperatureGrade.AUTOMOTIVE: (-40, 125),
        TemperatureGrade.MILITARY: (-55, 125),
    }
    return ranges.get(grade, (-40, 85))


def infer_power_profile(battery_powered: bool, battery_life_hours: Optional[int]) -> PowerProfile:
    """Infer power profile from battery requirements"""
    if not battery_powered:
        return PowerProfile.MODERATE_POWER
    
    if battery_life_hours and battery_life_hours > 8760:  # >1 year
        return PowerProfile.ULTRA_LOW_POWER
    elif battery_life_hours and battery_life_hours > 720:  # >1 month
        return PowerProfile.LOW_POWER
    else:
        return PowerProfile.MODERATE_POWER


def infer_performance_class(functions: List[str]) -> PerformanceClass:
    """Infer performance class from required functions"""
    high_perf_functions = {
        ComputeFunction.EDGE_AI,
        ComputeFunction.FFT_PROCESSING,
        ComputeFunction.SIGNAL_PROCESSING,
    }
    
    if any(f in high_perf_functions for f in functions):
        return PerformanceClass.HIGH_PERFORMANCE
    
    return PerformanceClass.MID_RANGE
