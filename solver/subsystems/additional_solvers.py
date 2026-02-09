"""
Additional Subsystem Solvers for HardwareGenius

Extends multi-subsystem solving to cover:
- Memory (Flash, EEPROM, SRAM, FRAM)
- Display (LCD, OLED, e-paper)
- Connectors (USB, Ethernet, headers)
- Protection (TVS, fuses, ESD)
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# Memory Solver
# ============================================================================

class MemoryRequirement(BaseModel):
    """Memory subsystem requirements"""
    memory_type: str  # flash, eeprom, sram, fram
    capacity_kb_min: int
    interface: str  # spi, i2c, parallel
    voltage: float = 3.3
    speed_mhz_min: Optional[int] = None
    low_power: bool = False


class MemoryRecommendation(BaseModel):
    """Memory component recommendation"""
    mpn: str
    manufacturer: str
    memory_type: str
    capacity_kb: int
    interface: str
    voltage: float
    speed_mhz: int
    power_ua: int
    package: str
    price_usd: float
    score: float
    evidence: List[str] = []


class MemorySolver:
    """Deterministic solver for memory components"""
    
    def __init__(self):
        # Curated memory database (will connect to real DB later)
        self.memory_db = self._init_memory_db()
    
    def _init_memory_db(self) -> List[Dict[str, Any]]:
        """Initialize curated memory component database"""
        return [
            # SPI Flash
            {
                "mpn": "W25Q128JV",
                "manufacturer": "Winbond",
                "memory_type": "flash",
                "capacity_kb": 16384,  # 16MB
                "interface": "spi",
                "voltage": 3.3,
                "speed_mhz": 133,
                "power_ua": 15000,  # active
                "package": "SOIC-8",
                "price_usd": 1.20
            },
            {
                "mpn": "MX25L6433F",
                "manufacturer": "Macronix",
                "memory_type": "flash",
                "capacity_kb": 8192,  # 8MB
                "interface": "spi",
                "voltage": 3.3,
                "speed_mhz": 104,
                "power_ua": 12000,
                "package": "SOIC-8",
                "price_usd": 0.80
            },
            # I2C EEPROM
            {
                "mpn": "24LC256",
                "manufacturer": "Microchip",
                "memory_type": "eeprom",
                "capacity_kb": 32,  # 256 Kbit
                "interface": "i2c",
                "voltage": 3.3,
                "speed_mhz": 1,  # 1MHz I2C
                "power_ua": 3000,
                "package": "SOIC-8",
                "price_usd": 0.50
            },
            {
                "mpn": "AT24C512C",
                "manufacturer": "Microchip",
                "memory_type": "eeprom",
                "capacity_kb": 64,  # 512 Kbit
                "interface": "i2c",
                "voltage": 3.3,
                "speed_mhz": 1,
                "power_ua": 3000,
                "package": "SOIC-8",
                "price_usd": 0.70
            },
            # SPI SRAM
            {
                "mpn": "23LC1024",
                "manufacturer": "Microchip",
                "memory_type": "sram",
                "capacity_kb": 128,  # 1Mbit
                "interface": "spi",
                "voltage": 3.3,
                "speed_mhz": 20,
                "power_ua": 4000,
                "package": "SOIC-8",
                "price_usd": 1.50
            },
            # FRAM
            {
                "mpn": "FM25V10",
                "manufacturer": "Cypress",
                "memory_type": "fram",
                "capacity_kb": 128,  # 1Mbit
                "interface": "spi",
                "voltage": 3.3,
                "speed_mhz": 40,
                "power_ua": 200,  # very low power
                "package": "SOIC-8",
                "price_usd": 2.50
            },
        ]
    
    def solve(self, req: MemoryRequirement) -> List[MemoryRecommendation]:
        """Find memory components matching requirements"""
        candidates = []
        
        for mem in self.memory_db:
            # Hard filters
            if mem["memory_type"] != req.memory_type:
                continue
            if mem["capacity_kb"] < req.capacity_kb_min:
                continue
            if mem["interface"] != req.interface:
                continue
            if abs(mem["voltage"] - req.voltage) > 0.3:
                continue
            if req.speed_mhz_min and mem["speed_mhz"] < req.speed_mhz_min:
                continue
            
            # Scoring
            score = 0.0
            
            # Capacity headroom (prefer some margin)
            headroom = (mem["capacity_kb"] - req.capacity_kb_min) / req.capacity_kb_min
            score += min(headroom * 10, 20)
            
            # Low power preference
            if req.low_power:
                power_score = max(0, 50 - mem["power_ua"] / 1000)
                score += power_score
            
            # Price (prefer lower cost)
            price_score = max(0, 20 - mem["price_usd"] * 5)
            score += price_score
            
            candidates.append(MemoryRecommendation(
                mpn=mem["mpn"],
                manufacturer=mem["manufacturer"],
                memory_type=mem["memory_type"],
                capacity_kb=mem["capacity_kb"],
                interface=mem["interface"],
                voltage=mem["voltage"],
                speed_mhz=mem["speed_mhz"],
                power_ua=mem["power_ua"],
                package=mem["package"],
                price_usd=mem["price_usd"],
                score=score,
                evidence=[f"Curated component: {mem['manufacturer']} {mem['mpn']}"]
            ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:5]


# ============================================================================
# Display Solver
# ============================================================================

class DisplayRequirement(BaseModel):
    """Display subsystem requirements"""
    display_type: str  # lcd, oled, epaper
    resolution: str  # "320x240", "128x64", etc.
    interface: str  # spi, i2c, parallel, mipi_dsi
    size_inches: Optional[float] = None
    touch: bool = False
    color: bool = True


class DisplayRecommendation(BaseModel):
    """Display component recommendation"""
    mpn: str
    manufacturer: str
    display_type: str
    resolution: str
    size_inches: float
    interface: str
    color: bool
    touch: bool
    price_usd: float
    score: float
    evidence: List[str] = []


class DisplaySolver:
    """Deterministic solver for display components"""
    
    def __init__(self):
        self.display_db = self._init_display_db()
    
    def _init_display_db(self) -> List[Dict[str, Any]]:
        """Initialize curated display database"""
        return [
            {
                "mpn": "SSD1306",
                "manufacturer": "Solomon Systech",
                "display_type": "oled",
                "resolution": "128x64",
                "size_inches": 0.96,
                "interface": "i2c",
                "color": False,
                "touch": False,
                "price_usd": 3.50
            },
            {
                "mpn": "ILI9341",
                "manufacturer": "ILI Technology",
                "display_type": "lcd",
                "resolution": "320x240",
                "size_inches": 2.4,
                "interface": "spi",
                "color": True,
                "touch": False,
                "price_usd": 8.00
            },
            {
                "mpn": "ST7789",
                "manufacturer": "Sitronix",
                "display_type": "lcd",
                "resolution": "240x240",
                "size_inches": 1.54,
                "interface": "spi",
                "color": True,
                "touch": False,
                "price_usd": 5.50
            },
            {
                "mpn": "GDEW042T2",
                "manufacturer": "Good Display",
                "display_type": "epaper",
                "resolution": "400x300",
                "size_inches": 4.2,
                "interface": "spi",
                "color": False,
                "touch": False,
                "price_usd": 15.00
            },
        ]
    
    def solve(self, req: DisplayRequirement) -> List[DisplayRecommendation]:
        """Find display components matching requirements"""
        candidates = []
        
        for disp in self.display_db:
            # Hard filters
            if disp["display_type"] != req.display_type:
                continue
            if disp["resolution"] != req.resolution:
                continue
            if disp["interface"] != req.interface:
                continue
            if req.color and not disp["color"]:
                continue
            if req.touch and not disp["touch"]:
                continue
            
            # Scoring
            score = 50.0  # base score
            
            # Size preference (if specified)
            if req.size_inches:
                size_diff = abs(disp["size_inches"] - req.size_inches)
                score += max(0, 20 - size_diff * 10)
            
            # Price
            price_score = max(0, 30 - disp["price_usd"])
            score += price_score
            
            candidates.append(DisplayRecommendation(
                mpn=disp["mpn"],
                manufacturer=disp["manufacturer"],
                display_type=disp["display_type"],
                resolution=disp["resolution"],
                size_inches=disp["size_inches"],
                interface=disp["interface"],
                color=disp["color"],
                touch=disp["touch"],
                price_usd=disp["price_usd"],
                score=score,
                evidence=[f"Curated component: {disp['manufacturer']} {disp['mpn']}"]
            ))
        
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:5]


# ============================================================================
# Connector Solver
# ============================================================================

class ConnectorRequirement(BaseModel):
    """Connector subsystem requirements"""
    connector_type: str  # usb, ethernet, header
    variant: Optional[str] = None  # usb_c, rj45, etc.
    pin_count: Optional[int] = None
    current_rating_a: Optional[float] = None


class ConnectorRecommendation(BaseModel):
    """Connector component recommendation"""
    mpn: str
    manufacturer: str
    connector_type: str
    variant: str
    pin_count: Optional[int]
    current_rating_a: float
    mounting: str
    price_usd: float
    score: float
    evidence: List[str] = []


class ConnectorSolver:
    """Deterministic solver for connector components"""
    
    def __init__(self):
        self.connector_db = self._init_connector_db()
    
    def _init_connector_db(self) -> List[Dict[str, Any]]:
        """Initialize curated connector database"""
        return [
            {
                "mpn": "TYPE-C-31-M-12",
                "manufacturer": "Korean Hroparts",
                "connector_type": "usb",
                "variant": "usb_c",
                "pin_count": 24,
                "current_rating_a": 3.0,
                "mounting": "smt",
                "price_usd": 0.50
            },
            {
                "mpn": "RJ45-8P8C",
                "manufacturer": "Amphenol",
                "connector_type": "ethernet",
                "variant": "rj45",
                "pin_count": 8,
                "current_rating_a": 1.5,
                "mounting": "through_hole",
                "price_usd": 0.80
            },
            {
                "mpn": "PH254-2x20",
                "manufacturer": "Generic",
                "connector_type": "header",
                "variant": "2.54mm_pitch",
                "pin_count": 40,
                "current_rating_a": 3.0,
                "mounting": "through_hole",
                "price_usd": 0.30
            },
        ]
    
    def solve(self, req: ConnectorRequirement) -> List[ConnectorRecommendation]:
        """Find connector components matching requirements"""
        candidates = []
        
        for conn in self.connector_db:
            # Hard filters
            if conn["connector_type"] != req.connector_type:
                continue
            if req.variant and conn["variant"] != req.variant:
                continue
            if req.pin_count and conn["pin_count"] != req.pin_count:
                continue
            if req.current_rating_a and conn["current_rating_a"] < req.current_rating_a:
                continue
            
            # Scoring
            score = 50.0
            score += max(0, 50 - conn["price_usd"] * 20)
            
            candidates.append(ConnectorRecommendation(
                mpn=conn["mpn"],
                manufacturer=conn["manufacturer"],
                connector_type=conn["connector_type"],
                variant=conn["variant"],
                pin_count=conn["pin_count"],
                current_rating_a=conn["current_rating_a"],
                mounting=conn["mounting"],
                price_usd=conn["price_usd"],
                score=score,
                evidence=[f"Curated component: {conn['manufacturer']} {conn['mpn']}"]
            ))
        
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:5]


# ============================================================================
# Protection Solver
# ============================================================================

class ProtectionRequirement(BaseModel):
    """Protection subsystem requirements"""
    protection_type: str  # tvs, fuse, esd
    voltage_max: float
    current_max_a: Optional[float] = None
    interface: Optional[str] = None  # for ESD protection


class ProtectionRecommendation(BaseModel):
    """Protection component recommendation"""
    mpn: str
    manufacturer: str
    protection_type: str
    voltage_max: float
    current_max_a: Optional[float]
    package: str
    price_usd: float
    score: float
    evidence: List[str] = []


class ProtectionSolver:
    """Deterministic solver for protection components"""
    
    def __init__(self):
        self.protection_db = self._init_protection_db()
    
    def _init_protection_db(self) -> List[Dict[str, Any]]:
        """Initialize curated protection component database"""
        return [
            {
                "mpn": "SMBJ5.0A",
                "manufacturer": "Littelfuse",
                "protection_type": "tvs",
                "voltage_max": 5.0,
                "current_max_a": None,
                "package": "SMB",
                "price_usd": 0.15
            },
            {
                "mpn": "SMBJ24A",
                "manufacturer": "Littelfuse",
                "protection_type": "tvs",
                "voltage_max": 24.0,
                "current_max_a": None,
                "package": "SMB",
                "price_usd": 0.18
            },
            {
                "mpn": "0ZCJ0050FF2G",
                "manufacturer": "Bel Fuse",
                "protection_type": "fuse",
                "voltage_max": 32.0,
                "current_max_a": 5.0,
                "package": "1206",
                "price_usd": 0.25
            },
            {
                "mpn": "TPD4E02B04",
                "manufacturer": "Texas Instruments",
                "protection_type": "esd",
                "voltage_max": 5.5,
                "current_max_a": None,
                "package": "SOT-23",
                "price_usd": 0.30
            },
        ]
    
    def solve(self, req: ProtectionRequirement) -> List[ProtectionRecommendation]:
        """Find protection components matching requirements"""
        candidates = []
        
        for prot in self.protection_db:
            # Hard filters
            if prot["protection_type"] != req.protection_type:
                continue
            if prot["voltage_max"] < req.voltage_max:
                continue
            if req.current_max_a and prot["current_max_a"] and prot["current_max_a"] < req.current_max_a:
                continue
            
            # Scoring
            score = 50.0
            
            # Voltage margin
            voltage_margin = (prot["voltage_max"] - req.voltage_max) / req.voltage_max
            score += min(voltage_margin * 20, 30)
            
            # Price
            score += max(0, 20 - prot["price_usd"] * 50)
            
            candidates.append(ProtectionRecommendation(
                mpn=prot["mpn"],
                manufacturer=prot["manufacturer"],
                protection_type=prot["protection_type"],
                voltage_max=prot["voltage_max"],
                current_max_a=prot["current_max_a"],
                package=prot["package"],
                price_usd=prot["price_usd"],
                score=score,
                evidence=[f"Curated component: {prot['manufacturer']} {prot['mpn']}"]
            ))
        
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:5]


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Memory solver example
    memory_solver = MemorySolver()
    mem_req = MemoryRequirement(
        memory_type="flash",
        capacity_kb_min=4096,
        interface="spi",
        low_power=True
    )
    mem_results = memory_solver.solve(mem_req)
    print(f"Memory recommendations: {len(mem_results)}")
    for rec in mem_results:
        print(f"  {rec.manufacturer} {rec.mpn}: {rec.capacity_kb}KB, ${rec.price_usd}, score={rec.score:.1f}")
    
    # Display solver example
    display_solver = DisplaySolver()
    disp_req = DisplayRequirement(
        display_type="lcd",
        resolution="320x240",
        interface="spi",
        color=True
    )
    disp_results = display_solver.solve(disp_req)
    print(f"\nDisplay recommendations: {len(disp_results)}")
    for rec in disp_results:
        print(f"  {rec.manufacturer} {rec.mpn}: {rec.resolution}, ${rec.price_usd}, score={rec.score:.1f}")
