"""
Multi-Subsystem Solvers for HardwareGenius Phase 2

Extends the deterministic solver to support multiple component categories:
- Power management (LDOs, buck converters, battery management)
- Communication transceivers (CAN, LoRa, BLE, etc.)
- Sensors (I2C, SPI, analog)

Each solver follows the same principles as MCU solver:
- Deterministic filtering
- Evidence-backed recommendations
- Explainable ranking
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Power Subsystem Models
# ============================================================================

class PowerComponentType(str, Enum):
    """Power component categories"""
    LDO = "ldo"
    BUCK_CONVERTER = "buck_converter"
    BOOST_CONVERTER = "boost_converter"
    BUCK_BOOST = "buck_boost"
    BATTERY_CHARGER = "battery_charger"
    LOAD_SWITCH = "load_switch"


class PowerComponent(BaseModel):
    """Power management component"""
    mpn: str
    manufacturer: str
    component_type: PowerComponentType
    
    # Electrical specs
    input_voltage_min: float
    input_voltage_max: float
    output_voltage: float
    output_current_ma: int
    
    # Efficiency
    efficiency_typical: Optional[float] = None
    quiescent_current_ua: Optional[int] = None
    
    # Features
    enable_pin: bool = False
    power_good_pin: bool = False
    adjustable_output: bool = False
    
    # Package
    package: str
    
    # Evidence
    evidence_urls: List[str] = Field(default_factory=list)


class PowerRequirements(BaseModel):
    """Power subsystem requirements"""
    component_type: PowerComponentType
    input_voltage_min: float
    input_voltage_max: float
    output_voltage: float
    output_current_ma: int
    efficiency_min: Optional[float] = None
    quiescent_current_ua_max: Optional[int] = None
    package_families: Optional[List[str]] = None


# ============================================================================
# Communication Subsystem Models
# ============================================================================

class TransceiverType(str, Enum):
    """Communication transceiver types"""
    CAN = "can"
    CAN_FD = "can_fd"
    RS485 = "rs485"
    RS232 = "rs232"
    LORA = "lora"
    ETHERNET_PHY = "ethernet_phy"


class Transceiver(BaseModel):
    """Communication transceiver component"""
    mpn: str
    manufacturer: str
    transceiver_type: TransceiverType
    
    # Specifications
    voltage_supply: float
    max_bitrate: Optional[int] = None  # bps
    
    # Features
    isolation: bool = False
    esd_protection: bool = False
    
    # Package
    package: str
    
    # Evidence
    evidence_urls: List[str] = Field(default_factory=list)


class TransceiverRequirements(BaseModel):
    """Transceiver requirements"""
    transceiver_type: TransceiverType
    voltage_supply: float
    min_bitrate: Optional[int] = None
    isolation_required: bool = False
    package_families: Optional[List[str]] = None


# ============================================================================
# Sensor Subsystem Models
# ============================================================================

class SensorType(str, Enum):
    """Sensor types"""
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    MAGNETOMETER = "magnetometer"
    LIGHT = "light"
    GAS = "gas"
    CURRENT = "current"
    VOLTAGE = "voltage"


class Sensor(BaseModel):
    """Sensor component"""
    mpn: str
    manufacturer: str
    sensor_type: SensorType
    
    # Interface
    interface: str  # i2c, spi, analog
    
    # Specifications
    voltage_supply_min: float
    voltage_supply_max: float
    current_consumption_ua: int
    
    # Performance
    resolution: Optional[str] = None
    accuracy: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    
    # Package
    package: str
    
    # Evidence
    evidence_urls: List[str] = Field(default_factory=list)


class SensorRequirements(BaseModel):
    """Sensor requirements"""
    sensor_type: SensorType
    interface: str
    voltage_supply: float
    max_current_ua: Optional[int] = None
    min_resolution: Optional[str] = None
    package_families: Optional[List[str]] = None


# ============================================================================
# Power Subsystem Solver
# ============================================================================

class PowerSolver:
    """Deterministic solver for power management components"""
    
    def __init__(self, database=None):
        self.database = database
        # In production, this would query a real database
        # For now, we'll use a curated list
        self.components = self._load_power_components()
    
    def _load_power_components(self) -> List[PowerComponent]:
        """Load power components from database or curated list"""
        # Curated list of common power components
        return [
            # LDOs
            PowerComponent(
                mpn="MCP1700-3302E/TO",
                manufacturer="Microchip",
                component_type=PowerComponentType.LDO,
                input_voltage_min=2.3,
                input_voltage_max=6.0,
                output_voltage=3.3,
                output_current_ma=250,
                quiescent_current_ua=2,
                efficiency_typical=0.85,
                package="TO-92",
                evidence_urls=["https://www.microchip.com/MCP1700"]
            ),
            PowerComponent(
                mpn="ADP150AUJZ-3.3",
                manufacturer="Analog Devices",
                component_type=PowerComponentType.LDO,
                input_voltage_min=2.2,
                input_voltage_max=5.5,
                output_voltage=3.3,
                output_current_ma=200,
                quiescent_current_ua=0.7,
                efficiency_typical=0.88,
                package="TSOT-5",
                evidence_urls=["https://www.analog.com/ADP150"]
            ),
            # Buck converters
            PowerComponent(
                mpn="TPS62160DGKR",
                manufacturer="Texas Instruments",
                component_type=PowerComponentType.BUCK_CONVERTER,
                input_voltage_min=3.0,
                input_voltage_max=17.0,
                output_voltage=3.3,
                output_current_ma=1000,
                efficiency_typical=0.92,
                quiescent_current_ua=17,
                adjustable_output=True,
                package="VSSOP-8",
                evidence_urls=["https://www.ti.com/TPS62160"]
            ),
        ]
    
    def solve(self, requirements: PowerRequirements) -> List[PowerComponent]:
        """
        Find power components matching requirements.
        
        Args:
            requirements: Power subsystem requirements
            
        Returns:
            List of matching components, ranked by suitability
        """
        # Hard filter
        candidates = self._hard_filter(requirements)
        
        # Rank
        ranked = self._rank(candidates, requirements)
        
        return ranked
    
    def _hard_filter(self, req: PowerRequirements) -> List[PowerComponent]:
        """Apply hard constraints"""
        candidates = []
        
        for component in self.components:
            # Component type match
            if component.component_type != req.component_type:
                continue
            
            # Voltage range
            if component.input_voltage_min > req.input_voltage_min:
                continue
            if component.input_voltage_max < req.input_voltage_max:
                continue
            
            # Output voltage (allow ±5% tolerance)
            if abs(component.output_voltage - req.output_voltage) / req.output_voltage > 0.05:
                if not component.adjustable_output:
                    continue
            
            # Output current
            if component.output_current_ma < req.output_current_ma:
                continue
            
            # Efficiency
            if req.efficiency_min and component.efficiency_typical:
                if component.efficiency_typical < req.efficiency_min:
                    continue
            
            # Quiescent current
            if req.quiescent_current_ua_max and component.quiescent_current_ua:
                if component.quiescent_current_ua > req.quiescent_current_ua_max:
                    continue
            
            candidates.append(component)
        
        return candidates
    
    def _rank(self, candidates: List[PowerComponent], req: PowerRequirements) -> List[PowerComponent]:
        """Rank candidates by suitability"""
        scored = []
        
        for component in candidates:
            score = 0.0
            
            # Efficiency (higher is better)
            if component.efficiency_typical:
                score += component.efficiency_typical * 30
            
            # Low quiescent current (lower is better)
            if component.quiescent_current_ua:
                # Normalize: 1µA = 10 points, 100µA = 0 points
                score += max(0, 10 - (component.quiescent_current_ua / 10))
            
            # Current headroom (some headroom is good, too much is wasteful)
            headroom_ratio = component.output_current_ma / req.output_current_ma
            if 1.2 <= headroom_ratio <= 2.0:
                score += 10
            elif headroom_ratio > 2.0:
                score += 5  # Too much headroom
            
            # Features
            if component.enable_pin:
                score += 2
            if component.power_good_pin:
                score += 2
            
            scored.append((score, component))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return [comp for score, comp in scored]


# ============================================================================
# Transceiver Subsystem Solver
# ============================================================================

class TransceiverSolver:
    """Deterministic solver for communication transceivers"""
    
    def __init__(self, database=None):
        self.database = database
        self.components = self._load_transceivers()
    
    def _load_transceivers(self) -> List[Transceiver]:
        """Load transceivers from database or curated list"""
        return [
            # CAN transceivers
            Transceiver(
                mpn="TJA1050T",
                manufacturer="NXP",
                transceiver_type=TransceiverType.CAN,
                voltage_supply=5.0,
                max_bitrate=1000000,
                esd_protection=True,
                package="SO-8",
                evidence_urls=["https://www.nxp.com/TJA1050"]
            ),
            Transceiver(
                mpn="SN65HVD230DR",
                manufacturer="Texas Instruments",
                transceiver_type=TransceiverType.CAN,
                voltage_supply=3.3,
                max_bitrate=1000000,
                esd_protection=True,
                package="SOIC-8",
                evidence_urls=["https://www.ti.com/SN65HVD230"]
            ),
            # LoRa modules
            Transceiver(
                mpn="RFM95W-915S2",
                manufacturer="HopeRF",
                transceiver_type=TransceiverType.LORA,
                voltage_supply=3.3,
                package="SMD",
                evidence_urls=["https://www.hoperf.com/RFM95W"]
            ),
        ]
    
    def solve(self, requirements: TransceiverRequirements) -> List[Transceiver]:
        """Find transceivers matching requirements"""
        candidates = self._hard_filter(requirements)
        ranked = self._rank(candidates, requirements)
        return ranked
    
    def _hard_filter(self, req: TransceiverRequirements) -> List[Transceiver]:
        """Apply hard constraints"""
        candidates = []
        
        for component in self.components:
            # Type match
            if component.transceiver_type != req.transceiver_type:
                continue
            
            # Voltage supply (allow ±10% tolerance)
            if abs(component.voltage_supply - req.voltage_supply) / req.voltage_supply > 0.1:
                continue
            
            # Bitrate
            if req.min_bitrate and component.max_bitrate:
                if component.max_bitrate < req.min_bitrate:
                    continue
            
            # Isolation
            if req.isolation_required and not component.isolation:
                continue
            
            candidates.append(component)
        
        return candidates
    
    def _rank(self, candidates: List[Transceiver], req: TransceiverRequirements) -> List[Transceiver]:
        """Rank candidates"""
        scored = []
        
        for component in candidates:
            score = 0.0
            
            # ESD protection
            if component.esd_protection:
                score += 10
            
            # Isolation (if not required but available, it's a bonus)
            if component.isolation:
                score += 5
            
            scored.append((score, component))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [comp for score, comp in scored]


# ============================================================================
# Sensor Subsystem Solver
# ============================================================================

class SensorSolver:
    """Deterministic solver for sensors"""
    
    def __init__(self, database=None):
        self.database = database
        self.components = self._load_sensors()
    
    def _load_sensors(self) -> List[Sensor]:
        """Load sensors from database or curated list"""
        return [
            # Temperature/Humidity
            Sensor(
                mpn="BME280",
                manufacturer="Bosch",
                sensor_type=SensorType.TEMPERATURE,
                interface="i2c",
                voltage_supply_min=1.71,
                voltage_supply_max=3.6,
                current_consumption_ua=3,
                resolution="0.01°C",
                accuracy="±1°C",
                package="LGA-8",
                evidence_urls=["https://www.bosch-sensortec.com/BME280"]
            ),
            # Accelerometer
            Sensor(
                mpn="ADXL345",
                manufacturer="Analog Devices",
                sensor_type=SensorType.ACCELEROMETER,
                interface="i2c",
                voltage_supply_min=2.0,
                voltage_supply_max=3.6,
                current_consumption_ua=40,
                resolution="13-bit",
                range_min=-16.0,
                range_max=16.0,
                package="LGA-14",
                evidence_urls=["https://www.analog.com/ADXL345"]
            ),
        ]
    
    def solve(self, requirements: SensorRequirements) -> List[Sensor]:
        """Find sensors matching requirements"""
        candidates = self._hard_filter(requirements)
        ranked = self._rank(candidates, requirements)
        return ranked
    
    def _hard_filter(self, req: SensorRequirements) -> List[Sensor]:
        """Apply hard constraints"""
        candidates = []
        
        for component in self.components:
            # Type match
            if component.sensor_type != req.sensor_type:
                continue
            
            # Interface match
            if component.interface != req.interface:
                continue
            
            # Voltage supply
            if component.voltage_supply_min > req.voltage_supply:
                continue
            if component.voltage_supply_max < req.voltage_supply:
                continue
            
            # Current consumption
            if req.max_current_ua and component.current_consumption_ua > req.max_current_ua:
                continue
            
            candidates.append(component)
        
        return candidates
    
    def _rank(self, candidates: List[Sensor], req: SensorRequirements) -> List[Sensor]:
        """Rank candidates"""
        scored = []
        
        for component in candidates:
            score = 0.0
            
            # Lower current consumption is better
            score += max(0, 20 - (component.current_consumption_ua / 10))
            
            scored.append((score, component))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [comp for score, comp in scored]
