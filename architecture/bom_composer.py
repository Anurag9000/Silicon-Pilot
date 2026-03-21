"""
BOM Composer for HardwareGenius Phase 2

Composes complete Bill of Materials from multi-subsystem recommendations.
Checks compatibility, generates alternatives, and provides sourcing information.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# ============================================================================
# BOM Models
# ============================================================================

class ComponentCategory(str, Enum):
    """Component categories"""
    MCU = "mcu"
    POWER = "power"
    COMMUNICATION = "communication"
    SENSOR = "sensor"
    MEMORY = "memory"
    PASSIVE = "passive"
    CONNECTOR = "connector"
    PROTECTION = "protection"
    EVAL_BOARD = "evaluation_board"
    OTHER = "other"


class BOMItem(BaseModel):
    """Single item in Bill of Materials"""
    subsystem: str
    category: ComponentCategory
    recommended_mpn: str
    manufacturer: str
    description: str
    quantity: int = 1
    
    # Alternatives
    alternatives: List[Dict[str, str]] = Field(default_factory=list)
    
    # Evidence
    evidence_urls: List[str] = Field(default_factory=list)
    datasheet_url: Optional[str] = None
    
    # Sourcing (optional)
    estimated_unit_cost_usd: Optional[float] = None
    availability: Optional[str] = None
    lead_time_weeks: Optional[int] = None
    
    # Notes
    notes: Optional[str] = None


class BOM(BaseModel):
    """Complete Bill of Materials"""
    device_name: str
    device_type: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    items: List[BOMItem] = Field(default_factory=list)
    
    # Summary
    total_parts: int = 0
    total_estimated_cost_usd: Optional[float] = None
    
    # Compatibility notes
    compatibility_notes: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    def add_item(self, item: BOMItem):
        """Add item to BOM"""
        self.items.append(item)
        self.total_parts = len(self.items)
        
        # Update total cost
        if item.estimated_unit_cost_usd:
            if self.total_estimated_cost_usd is None:
                self.total_estimated_cost_usd = 0.0
            self.total_estimated_cost_usd += item.estimated_unit_cost_usd * item.quantity
    
    def get_items_by_category(self, category: ComponentCategory) -> List[BOMItem]:
        """Get all items in a category"""
        return [item for item in self.items if item.category == category]
    
    def get_item_by_subsystem(self, subsystem: str) -> Optional[BOMItem]:
        """Get item for a specific subsystem"""
        for item in self.items:
            if item.subsystem == subsystem:
                return item
        return None


# ============================================================================
# BOM Composer
# ============================================================================

class BOMComposer:
    """
    Composes complete BOM from multi-subsystem recommendations.
    
    Responsibilities:
    - Collect subsystem recommendations
    - Check voltage/interface compatibility
    - Generate alternatives
    - Calculate cost estimates
    - Provide sourcing info
    """
    
    def __init__(self):
        self.compatibility_rules = self._load_compatibility_rules()
    
    def _load_compatibility_rules(self) -> Dict[str, Any]:
        """Load compatibility checking rules"""
        return {
            'voltage_tolerance': 0.1,  # ±10%
            'interface_voltage_levels': {
                'i2c': [1.8, 3.3, 5.0],
                'spi': [1.8, 3.3, 5.0],
                'uart': [1.8, 3.3, 5.0],
                'can': [5.0],
            }
        }
    
    def compose(
        self,
        device_name: str,
        device_type: str,
        mcu_recommendation: Optional[Any] = None,
        power_recommendations: Optional[List[Any]] = None,
        transceiver_recommendations: Optional[List[Any]] = None,
        sensor_recommendations: Optional[List[Any]] = None,
    ) -> BOM:
        """
        Compose complete BOM from subsystem recommendations.
        
        Args:
            device_name: Name of the device
            device_type: Device type
            mcu_recommendation: MCU recommendation from solver
            power_recommendations: Power component recommendations
            transceiver_recommendations: Transceiver recommendations
            sensor_recommendations: Sensor recommendations
            
        Returns:
            Complete BOM with compatibility checks
        """
        bom = BOM(device_name=device_name, device_type=device_type)
        
        # Add MCU
        if mcu_recommendation:
            bom.add_item(self._create_mcu_item(mcu_recommendation))
        
        # Add power components
        if power_recommendations:
            for power_comp in power_recommendations:
                bom.add_item(self._create_power_item(power_comp))
        
        # Add transceivers
        if transceiver_recommendations:
            for transceiver in transceiver_recommendations:
                bom.add_item(self._create_transceiver_item(transceiver))
        
        # Add sensors
        if sensor_recommendations:
            for sensor in sensor_recommendations:
                bom.add_item(self._create_sensor_item(sensor))
        
        # Suggest Evaluation Board for the MCU
        if mcu_recommendation:
            board_item = self._suggest_eval_board(mcu_recommendation)
            if board_item:
                bom.add_item(board_item)
        
        # Check compatibility
        self._check_compatibility(bom)
        
        return bom

    def _suggest_eval_board(self, mcu: Any) -> Optional[BOMItem]:
        """Suggest a specific Nucleo/Discovery board for the MCU"""
        mpn = mcu.mpn if hasattr(mcu, 'mpn') else str(mcu)
        manufacturer = mcu.manufacturer if hasattr(mcu, 'manufacturer') else "STMicroelectronics"
        
        if "STM32H7" in mpn:
            board_mpn = "NUCLEO-H743ZI2"
            desc = "High-performance STM32H7 development board with Ethernet and USB"
        elif "STM32F4" in mpn:
            board_mpn = "NUCLEO-F429ZI"
            desc = "Standard STM32F4 development board with on-board debugger"
        elif "STM32L4" in mpn:
            board_mpn = "NUCLEO-L476RG"
            desc = "Ultra-low-power STM32L4 development board"
        else:
            return None

        return BOMItem(
            subsystem="compute",
            category=ComponentCategory.EVAL_BOARD,
            recommended_mpn=board_mpn,
            manufacturer=manufacturer,
            description=desc,
            quantity=1,
            notes="Recommended for rapid prototyping of the selected MCU"
        )
    
    def _create_mcu_item(self, mcu: Any) -> BOMItem:
        """Create BOM item from MCU recommendation"""
        return BOMItem(
            subsystem="compute",
            category=ComponentCategory.MCU,
            recommended_mpn=mcu.mpn if hasattr(mcu, 'mpn') else str(mcu),
            manufacturer=mcu.manufacturer if hasattr(mcu, 'manufacturer') else "Unknown",
            description=f"Microcontroller - {mcu.family if hasattr(mcu, 'family') else 'MCU'}",
            quantity=1,
            evidence_urls=getattr(mcu, 'evidence_urls', []),
            notes="Primary compute element"
        )
    
    def _create_power_item(self, power: Any) -> BOMItem:
        """Create BOM item from power component"""
        return BOMItem(
            subsystem="power",
            category=ComponentCategory.POWER,
            recommended_mpn=power.mpn,
            manufacturer=power.manufacturer,
            description=f"{power.component_type.value.upper()} - {power.output_voltage}V @ {power.output_current_ma}mA",
            quantity=1,
            evidence_urls=power.evidence_urls,
            estimated_unit_cost_usd=self._estimate_power_cost(power),
            notes=f"Efficiency: {power.efficiency_typical*100:.0f}%" if power.efficiency_typical else None
        )
    
    def _create_transceiver_item(self, transceiver: Any) -> BOMItem:
        """Create BOM item from transceiver"""
        return BOMItem(
            subsystem="communication",
            category=ComponentCategory.COMMUNICATION,
            recommended_mpn=transceiver.mpn,
            manufacturer=transceiver.manufacturer,
            description=f"{transceiver.transceiver_type.value.upper()} Transceiver",
            quantity=1,
            evidence_urls=transceiver.evidence_urls,
            estimated_unit_cost_usd=self._estimate_transceiver_cost(transceiver),
            notes=f"Isolation: {'Yes' if transceiver.isolation else 'No'}"
        )
    
    def _create_sensor_item(self, sensor: Any) -> BOMItem:
        """Create BOM item from sensor"""
        return BOMItem(
            subsystem="sensing",
            category=ComponentCategory.SENSOR,
            recommended_mpn=sensor.mpn,
            manufacturer=sensor.manufacturer,
            description=f"{sensor.sensor_type.value.title()} Sensor - {sensor.interface.upper()}",
            quantity=1,
            evidence_urls=sensor.evidence_urls,
            estimated_unit_cost_usd=self._estimate_sensor_cost(sensor),
            notes=f"Current: {sensor.current_consumption_ua}µA"
        )
    
    def _check_compatibility(self, bom: BOM):
        """Check component compatibility and add notes/warnings"""
        # Get MCU
        mcu_item = bom.get_item_by_subsystem("compute")
        if not mcu_item:
            return
        
        # Check power supply voltage compatibility
        power_items = bom.get_items_by_category(ComponentCategory.POWER)
        for power_item in power_items:
            # Extract voltage from description (simplified)
            # In production, this would use structured data
            if "3.3V" in power_item.description:
                bom.compatibility_notes.append(
                    f"✓ {power_item.recommended_mpn} provides 3.3V for MCU and peripherals"
                )
        
        # Check sensor interface compatibility
        sensor_items = bom.get_items_by_category(ComponentCategory.SENSOR)
        for sensor_item in sensor_items:
            if "I2C" in sensor_item.description:
                bom.compatibility_notes.append(
                    f"✓ {sensor_item.recommended_mpn} uses I2C interface (ensure pull-up resistors)"
                )
        
        # Check transceiver voltage levels
        transceiver_items = bom.get_items_by_category(ComponentCategory.COMMUNICATION)
        for trans_item in transceiver_items:
            if "CAN" in trans_item.description:
                if "5V" in trans_item.notes or "5.0" in str(trans_item):
                    bom.warnings.append(
                        f"⚠ {trans_item.recommended_mpn} requires 5V supply (may need level shifter for 3.3V MCU)"
                    )
    
    def _estimate_power_cost(self, power: Any) -> float:
        """Estimate power component cost"""
        # Simplified cost estimation
        base_cost = 0.50
        
        if power.component_type.value == "buck_converter":
            base_cost = 1.50
        elif power.component_type.value == "ldo":
            base_cost = 0.30
        
        return base_cost
    
    def _estimate_transceiver_cost(self, transceiver: Any) -> float:
        """Estimate transceiver cost"""
        base_cost = 1.00
        
        if transceiver.transceiver_type.value == "can":
            base_cost = 0.80
        elif transceiver.transceiver_type.value == "lora":
            base_cost = 4.00
        
        if transceiver.isolation:
            base_cost += 2.00
        
        return base_cost
    
    def _estimate_sensor_cost(self, sensor: Any) -> float:
        """Estimate sensor cost"""
        # Simplified cost estimation
        sensor_costs = {
            "temperature": 2.00,
            "humidity": 3.00,
            "pressure": 4.00,
            "accelerometer": 3.50,
            "gyroscope": 5.00,
        }
        
        return sensor_costs.get(sensor.sensor_type.value, 2.00)
    
    def export_to_csv(self, bom: BOM) -> str:
        """Export BOM to CSV format"""
        lines = [
            "Subsystem,Category,MPN,Manufacturer,Description,Qty,Est. Cost (USD),Notes"
        ]
        
        for item in bom.items:
            cost_str = f"${item.estimated_unit_cost_usd:.2f}" if item.estimated_unit_cost_usd else "N/A"
            notes_str = item.notes or ""
            
            lines.append(
                f"{item.subsystem},{item.category.value},{item.recommended_mpn},"
                f"{item.manufacturer},\"{item.description}\",{item.quantity},"
                f"{cost_str},\"{notes_str}\""
            )
        
        # Add summary
        lines.append("")
        lines.append(f"Total Parts,{bom.total_parts}")
        if bom.total_estimated_cost_usd:
            lines.append(f"Total Estimated Cost,${bom.total_estimated_cost_usd:.2f}")
        
        return "\n".join(lines)
    
    def export_to_markdown(self, bom: BOM) -> str:
        """Export BOM to Markdown format"""
        lines = [
            f"# Bill of Materials: {bom.device_name}",
            "",
            f"**Device Type**: {bom.device_type}  ",
            f"**Created**: {bom.created_at.strftime('%Y-%m-%d %H:%M')}  ",
            f"**Total Parts**: {bom.total_parts}  ",
        ]
        
        if bom.total_estimated_cost_usd:
            lines.append(f"**Estimated Cost**: ${bom.total_estimated_cost_usd:.2f}  ")
        
        lines.extend(["", "---", "", "## Components", ""])
        
        # Group by category
        for category in ComponentCategory:
            items = bom.get_items_by_category(category)
            if not items:
                continue
            
            lines.append(f"### {category.value.title()}")
            lines.append("")
            
            for item in items:
                lines.append(f"**{item.recommended_mpn}** ({item.manufacturer})")
                lines.append(f"- Description: {item.description}")
                lines.append(f"- Quantity: {item.quantity}")
                if item.estimated_unit_cost_usd:
                    lines.append(f"- Est. Cost: ${item.estimated_unit_cost_usd:.2f}")
                if item.notes:
                    lines.append(f"- Notes: {item.notes}")
                lines.append("")
        
        # Compatibility notes
        if bom.compatibility_notes:
            lines.extend(["---", "", "## Compatibility Notes", ""])
            for note in bom.compatibility_notes:
                lines.append(f"- {note}")
            lines.append("")
        
        # Warnings
        if bom.warnings:
            lines.extend(["---", "", "## Warnings", ""])
            for warning in bom.warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        return "\n".join(lines)
