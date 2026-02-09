"""
Configuration Notes Generator for HardwareGenius Phase 2

Generates implementation guidance for recommended hardware:
- Clock tree configuration
- Pin mux assignments
- Power budget analysis
- Firmware stack recommendations
- Design notes and best practices
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from core.ontology import ArchitectureGraph
from architecture.bom_composer import BOM, BOMItem


# ============================================================================
# Configuration Models
# ============================================================================

class ClockConfiguration(BaseModel):
    """Clock tree configuration"""
    external_crystal_mhz: Optional[float] = None
    pll_config: Optional[str] = None
    system_clock_mhz: int
    peripheral_clocks: Dict[str, int] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class PinAssignment(BaseModel):
    """Pin assignment for a peripheral"""
    peripheral: str
    function: str
    pins: List[str]
    notes: Optional[str] = None


class PowerBudget(BaseModel):
    """Power consumption budget"""
    component: str
    typical_ma: float
    max_ma: float
    voltage: float
    notes: Optional[str] = None


class FirmwareStack(BaseModel):
    """Recommended firmware stack"""
    hal_library: str
    rtos: Optional[str] = None
    middleware: List[str] = Field(default_factory=list)
    drivers: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ConfigurationNotes(BaseModel):
    """Complete configuration notes"""
    device_name: str
    
    clock_config: Optional[ClockConfiguration] = None
    pin_assignments: List[PinAssignment] = Field(default_factory=list)
    power_budget: List[PowerBudget] = Field(default_factory=list)
    firmware_stack: Optional[FirmwareStack] = None
    
    design_notes: List[str] = Field(default_factory=list)
    best_practices: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Configuration Generator
# ============================================================================

class ConfigurationGenerator:
    """
    Generates configuration notes from architecture and BOM.
    
    Provides actionable implementation guidance.
    """
    
    def __init__(self):
        self.mcu_configs = self._load_mcu_configs()
    
    def _load_mcu_configs(self) -> Dict[str, Any]:
        """Load MCU-specific configuration templates"""
        return {
            'stm32f4': {
                'hal_library': 'STM32CubeF4',
                'typical_crystal_mhz': 8.0,
                'max_system_clock_mhz': 168,
                'peripheral_buses': {
                    'APB1': 42,
                    'APB2': 84,
                }
            },
            'stm32l4': {
                'hal_library': 'STM32CubeL4',
                'typical_crystal_mhz': 8.0,
                'max_system_clock_mhz': 80,
                'peripheral_buses': {
                    'APB1': 80,
                    'APB2': 80,
                }
            },
        }
    
    def generate(
        self,
        architecture: ArchitectureGraph,
        bom: BOM,
        answers: Optional[Dict[str, Any]] = None
    ) -> ConfigurationNotes:
        """
        Generate configuration notes.
        
        Args:
            architecture: Architecture graph
            bom: Bill of materials
            answers: User answers from template questions
            
        Returns:
            Complete configuration notes
        """
        config = ConfigurationNotes(device_name=bom.device_name)
        
        # Generate clock configuration
        config.clock_config = self._generate_clock_config(bom, architecture)
        
        # Generate pin assignments
        config.pin_assignments = self._generate_pin_assignments(architecture, answers)
        
        # Generate power budget
        config.power_budget = self._generate_power_budget(bom)
        
        # Generate firmware stack recommendations
        config.firmware_stack = self._generate_firmware_stack(bom, architecture)
        
        # Generate design notes
        config.design_notes = self._generate_design_notes(architecture, bom, answers)
        
        # Generate best practices
        config.best_practices = self._generate_best_practices(architecture)
        
        # Generate warnings
        config.warnings = self._generate_warnings(architecture, bom)
        
        return config
    
    def _generate_clock_config(self, bom: BOM, architecture: ArchitectureGraph) -> ClockConfiguration:
        """Generate clock tree configuration"""
        mcu_item = bom.get_item_by_subsystem("compute")
        if not mcu_item:
            return ClockConfiguration(system_clock_mhz=48)
        
        # Detect MCU family from MPN
        mpn_lower = mcu_item.recommended_mpn.lower()
        
        if 'stm32f4' in mpn_lower:
            return ClockConfiguration(
                external_crystal_mhz=8.0,
                pll_config="HSE 8MHz → PLL → 168MHz",
                system_clock_mhz=168,
                peripheral_clocks={
                    'APB1': 42,
                    'APB2': 84,
                    'AHB': 168,
                },
                notes=[
                    "Use external 8 MHz crystal for accurate timing",
                    "PLL configured for maximum 168 MHz system clock",
                    "CAN peripheral requires APB1 clock (42 MHz max)",
                ]
            )
        elif 'stm32l4' in mpn_lower:
            return ClockConfiguration(
                external_crystal_mhz=8.0,
                pll_config="HSE 8MHz → PLL → 80MHz",
                system_clock_mhz=80,
                peripheral_clocks={
                    'APB1': 80,
                    'APB2': 80,
                    'AHB': 80,
                },
                notes=[
                    "MSI can be used for ultra-low-power operation",
                    "LSE 32.768 kHz for RTC",
                ]
            )
        else:
            return ClockConfiguration(
                system_clock_mhz=48,
                notes=["Generic configuration - refer to MCU datasheet"]
            )
    
    def _generate_pin_assignments(
        self,
        architecture: ArchitectureGraph,
        answers: Optional[Dict[str, Any]]
    ) -> List[PinAssignment]:
        """Generate pin assignment suggestions"""
        assignments = []
        
        # Get required interfaces
        interfaces = architecture.get_all_required_interfaces()
        
        # Motor control pins (if motor controller)
        if architecture.device_type.value == "motor_controller":
            assignments.append(PinAssignment(
                peripheral="TIM1",
                function="Motor PWM",
                pins=["PA8 (CH1)", "PA9 (CH2)", "PA10 (CH3)"],
                notes="3-phase BLDC motor control"
            ))
            assignments.append(PinAssignment(
                peripheral="ADC1",
                function="Current Sense",
                pins=["PA0 (IN0)", "PA1 (IN1)", "PA2 (IN2)"],
                notes="Phase current measurement"
            ))
        
        # CAN interface
        if any('can' in str(iface).lower() for iface in interfaces):
            assignments.append(PinAssignment(
                peripheral="CAN1",
                function="CAN Bus",
                pins=["PB8 (RX)", "PB9 (TX)"],
                notes="Connect to CAN transceiver"
            ))
        
        # I2C sensors
        if any('i2c' in str(iface).lower() for iface in interfaces):
            assignments.append(PinAssignment(
                peripheral="I2C1",
                function="Sensor Bus",
                pins=["PB6 (SCL)", "PB7 (SDA)"],
                notes="Requires 4.7kΩ pull-up resistors"
            ))
        
        # SPI
        if any('spi' in str(iface).lower() for iface in interfaces):
            assignments.append(PinAssignment(
                peripheral="SPI1",
                function="SPI Bus",
                pins=["PA5 (SCK)", "PA6 (MISO)", "PA7 (MOSI)"],
                notes="For LoRa module or external flash"
            ))
        
        # SD card
        if any('sdmmc' in str(iface).lower() for iface in interfaces):
            assignments.append(PinAssignment(
                peripheral="SDMMC1",
                function="SD Card",
                pins=["PC8-PC12 (D0-D3, CLK, CMD)"],
                notes="4-bit SDMMC interface"
            ))
        
        return assignments
    
    def _generate_power_budget(self, bom: BOM) -> List[PowerBudget]:
        """Generate power consumption budget"""
        budget = []
        
        # MCU
        mcu_item = bom.get_item_by_subsystem("compute")
        if mcu_item:
            budget.append(PowerBudget(
                component="MCU",
                typical_ma=50.0,
                max_ma=100.0,
                voltage=3.3,
                notes="Active at full speed, typical workload"
            ))
        
        # Sensors
        sensor_items = [item for item in bom.items if item.category.value == "sensor"]
        for sensor in sensor_items:
            # Extract current from notes if available
            current_ua = 50  # Default
            if sensor.notes and "µA" in sensor.notes:
                try:
                    current_ua = int(sensor.notes.split("Current: ")[1].split("µA")[0])
                except:
                    pass
            
            budget.append(PowerBudget(
                component=f"Sensor: {sensor.recommended_mpn}",
                typical_ma=current_ua / 1000.0,
                max_ma=current_ua / 1000.0,
                voltage=3.3,
                notes=sensor.description
            ))
        
        # Transceivers
        transceiver_items = [item for item in bom.items if item.category.value == "communication"]
        for trans in transceiver_items:
            if "CAN" in trans.description:
                budget.append(PowerBudget(
                    component=f"CAN Transceiver: {trans.recommended_mpn}",
                    typical_ma=70.0,
                    max_ma=100.0,
                    voltage=5.0,
                    notes="CAN transceiver active"
                ))
            elif "LoRa" in trans.description:
                budget.append(PowerBudget(
                    component=f"LoRa Module: {trans.recommended_mpn}",
                    typical_ma=15.0,
                    max_ma=120.0,
                    voltage=3.3,
                    notes="Sleep: 1µA, RX: 15mA, TX: 120mA"
                ))
        
        # Calculate total
        total_typical = sum(item.typical_ma for item in budget)
        total_max = sum(item.max_ma for item in budget)
        
        budget.append(PowerBudget(
            component="TOTAL",
            typical_ma=total_typical,
            max_ma=total_max,
            voltage=3.3,
            notes=f"Total system power budget"
        ))
        
        return budget
    
    def _generate_firmware_stack(self, bom: BOM, architecture: ArchitectureGraph) -> FirmwareStack:
        """Generate firmware stack recommendations"""
        mcu_item = bom.get_item_by_subsystem("compute")
        if not mcu_item:
            return FirmwareStack(hal_library="Generic HAL")
        
        mpn_lower = mcu_item.recommended_mpn.lower()
        
        if 'stm32' in mpn_lower:
            family = 'f4' if 'f4' in mpn_lower else 'l4' if 'l4' in mpn_lower else 'f1'
            
            stack = FirmwareStack(
                hal_library=f"STM32Cube{family.upper()}",
                rtos="FreeRTOS" if architecture.device_type.value == "motor_controller" else None,
                middleware=[],
                drivers=[],
                notes=[
                    f"Use STM32CubeMX for initialization code generation",
                    f"HAL library provides hardware abstraction",
                ]
            )
            
            # Add middleware based on device type
            if architecture.device_type.value == "motor_controller":
                stack.middleware.append("Motor Control SDK")
                stack.notes.append("STM32 Motor Control SDK provides FOC algorithms")
            
            # Add drivers based on components
            for item in bom.items:
                if "BME280" in item.recommended_mpn:
                    stack.drivers.append("BME280 I2C driver")
                elif "LoRa" in item.description:
                    stack.drivers.append("LoRa SPI driver (e.g., RadioLib)")
            
            return stack
        
        return FirmwareStack(hal_library="Vendor HAL")
    
    def _generate_design_notes(
        self,
        architecture: ArchitectureGraph,
        bom: BOM,
        answers: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate design notes"""
        notes = []
        
        # Device-specific notes
        if architecture.device_type.value == "motor_controller":
            notes.append("**Motor Control**: Implement Field-Oriented Control (FOC) for BLDC motors")
            notes.append("**Current Sensing**: Use inline shunt resistors (e.g., 0.01Ω) for phase current measurement")
            notes.append("**Gate Drivers**: Ensure gate driver can handle motor voltage and current")
        
        elif architecture.device_type.value == "sensor_node":
            notes.append("**Power Optimization**: Use deep sleep modes between sensor readings")
            notes.append("**Wireless**: Implement duty-cycled transmission to conserve battery")
            notes.append("**RTC**: Use LSE crystal for accurate timekeeping in sleep mode")
        
        elif architecture.device_type.value == "data_logger":
            notes.append("**SD Card**: Use FAT32 filesystem for compatibility")
            notes.append("**Data Format**: Consider CSV or binary format for logged data")
            notes.append("**RTC**: Battery backup for RTC to maintain timestamps during power loss")
        
        # Component-specific notes
        for item in bom.items:
            if "I2C" in item.description:
                notes.append(f"**{item.recommended_mpn}**: Requires 4.7kΩ pull-up resistors on SDA/SCL")
        
        return notes
    
    def _generate_best_practices(self, architecture: ArchitectureGraph) -> List[str]:
        """Generate best practices"""
        practices = [
            "Add decoupling capacitors (100nF ceramic + 10µF tantalum) near each IC",
            "Use ground plane for EMI reduction",
            "Keep high-speed traces (SPI, SDMMC) short and impedance-matched",
            "Add ESD protection on external connectors",
            "Include test points for debugging critical signals",
        ]
        
        if architecture.device_type.value == "motor_controller":
            practices.extend([
                "Separate analog and digital grounds, connect at single point",
                "Use thick traces for high-current paths",
                "Add snubber circuits across motor phases",
            ])
        
        return practices
    
    def _generate_warnings(self, architecture: ArchitectureGraph, bom: BOM) -> List[str]:
        """Generate warnings"""
        warnings = []
        
        # Check for 5V components with 3.3V MCU
        mcu_item = bom.get_item_by_subsystem("compute")
        if mcu_item and "3.3" in str(mcu_item):
            for item in bom.items:
                if "5V" in item.description or "5.0" in str(item):
                    warnings.append(
                        f"⚠ {item.recommended_mpn} operates at 5V - may require level shifter for 3.3V MCU"
                    )
        
        # Power budget warnings
        power_items = [item for item in bom.items if item.category.value == "power"]
        if power_items:
            for power in power_items:
                if "250mA" in power.description:
                    warnings.append(
                        f"⚠ {power.recommended_mpn} limited to 250mA - verify total system current"
                    )
        
        return warnings
    
    def export_to_markdown(self, config: ConfigurationNotes) -> str:
        """Export configuration notes to Markdown"""
        lines = [
            f"# Configuration Notes: {config.device_name}",
            "",
            "---",
            "",
        ]
        
        # Clock configuration
        if config.clock_config:
            lines.extend([
                "## Clock Configuration",
                "",
                f"**System Clock**: {config.clock_config.system_clock_mhz} MHz  ",
            ])
            
            if config.clock_config.external_crystal_mhz:
                lines.append(f"**External Crystal**: {config.clock_config.external_crystal_mhz} MHz  ")
            
            if config.clock_config.pll_config:
                lines.append(f"**PLL**: {config.clock_config.pll_config}  ")
            
            if config.clock_config.peripheral_clocks:
                lines.append("")
                lines.append("**Peripheral Clocks**:")
                for bus, freq in config.clock_config.peripheral_clocks.items():
                    lines.append(f"- {bus}: {freq} MHz")
            
            if config.clock_config.notes:
                lines.append("")
                for note in config.clock_config.notes:
                    lines.append(f"- {note}")
            
            lines.append("")
        
        # Pin assignments
        if config.pin_assignments:
            lines.extend(["---", "", "## Pin Assignments", ""])
            
            for assignment in config.pin_assignments:
                lines.append(f"### {assignment.peripheral} - {assignment.function}")
                lines.append("")
                for pin in assignment.pins:
                    lines.append(f"- {pin}")
                if assignment.notes:
                    lines.append(f"- **Note**: {assignment.notes}")
                lines.append("")
        
        # Power budget
        if config.power_budget:
            lines.extend(["---", "", "## Power Budget", ""])
            lines.append("| Component | Typical (mA) | Max (mA) | Voltage (V) | Notes |")
            lines.append("|-----------|--------------|----------|-------------|-------|")
            
            for item in config.power_budget:
                notes = item.notes or ""
                lines.append(
                    f"| {item.component} | {item.typical_ma:.1f} | {item.max_ma:.1f} | "
                    f"{item.voltage:.1f} | {notes} |"
                )
            
            lines.append("")
        
        # Firmware stack
        if config.firmware_stack:
            lines.extend(["---", "", "## Firmware Stack", ""])
            lines.append(f"**HAL Library**: {config.firmware_stack.hal_library}  ")
            
            if config.firmware_stack.rtos:
                lines.append(f"**RTOS**: {config.firmware_stack.rtos}  ")
            
            if config.firmware_stack.middleware:
                lines.append("")
                lines.append("**Middleware**:")
                for mw in config.firmware_stack.middleware:
                    lines.append(f"- {mw}")
            
            if config.firmware_stack.drivers:
                lines.append("")
                lines.append("**Drivers**:")
                for driver in config.firmware_stack.drivers:
                    lines.append(f"- {driver}")
            
            if config.firmware_stack.notes:
                lines.append("")
                for note in config.firmware_stack.notes:
                    lines.append(f"- {note}")
            
            lines.append("")
        
        # Design notes
        if config.design_notes:
            lines.extend(["---", "", "## Design Notes", ""])
            for note in config.design_notes:
                lines.append(f"{note}  ")
            lines.append("")
        
        # Best practices
        if config.best_practices:
            lines.extend(["---", "", "## Best Practices", ""])
            for practice in config.best_practices:
                lines.append(f"- {practice}")
            lines.append("")
        
        # Warnings
        if config.warnings:
            lines.extend(["---", "", "## ⚠️ Warnings", ""])
            for warning in config.warnings:
                lines.append(f"{warning}  ")
            lines.append("")
        
        return "\n".join(lines)
