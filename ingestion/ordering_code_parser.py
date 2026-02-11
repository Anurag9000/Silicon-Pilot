"""
Enhanced STM32 Ordering Code Parser

Parses complete STM32 ordering codes to extract all variants:
- Temperature range
- Package type
- Flash size
- Voltage range
- Pin count

Example: STM32F405RGT6
- STM32 = Product line
- F = General purpose
- 405 = Part number
- R = Pin count (64 pins)
- G = Flash size (1024 KB)
- T = Package (LQFP)
- 6 = Temperature range (-40 to 85°C)
"""

import re
from typing import Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class OrderingCodeVariant:
    """Parsed ordering code variant"""
    full_code: str
    family: str
    series: str
    part_number: str
    pin_count: int
    flash_kb: int
    package: str
    temperature_range: str
    temperature_min_c: int
    temperature_max_c: int
    voltage_range: Optional[str] = None
    
class OrderingCodeParser:
    """Parse STM32 ordering codes"""
    
    def __init__(self):
        # Pin count mapping (letter -> count)
        self.pin_counts = {
            'C': 48, 'R': 64, 'V': 100, 'Z': 144, 'I': 176, 'B': 128,
            'M': 81, 'N': 216, 'A': 169, 'F': 20, 'G': 28, 'K': 32,
            'T': 36, 'H': 40, 'U': 63, 'Y': 114, 'E': 512
        }
        
        # Flash size mapping (letter -> KB)
        self.flash_sizes = {
            '4': 16, '6': 32, '8': 64, 'B': 128, 'C': 256, 'D': 384,
            'E': 512, 'F': 768, 'G': 1024, 'H': 1536, 'I': 2048,
            'Z': 192, 'Y': 320
        }
        
        # Package mapping
        self.packages = {
            'T': 'LQFP', 'H': 'BGA', 'U': 'VFQFPN', 'Y': 'WLCSP',
            'P': 'TSSOP', 'J': 'UFQFPN', 'K': 'UFBGA', 'M': 'SO',
            'Q': 'UFQFPN', 'S': 'WLCSP', 'C': 'LQFP', 'R': 'LQFP',
            'V': 'LQFP', 'Z': 'LQFP', 'I': 'LQFP', 'B': 'LQFP',
            'A': 'BGA', 'N': 'BGA', 'E': 'LFBGA'
        }
        
        # Temperature range mapping
        self.temp_ranges = {
            '6': {'range': 'Industrial', 'min': -40, 'max': 85},
            '7': {'range': 'Industrial', 'min': -40, 'max': 85},
            'Y': {'range': 'Extended', 'min': -40, 'max': 105},
            '3': {'range': 'Automotive', 'min': -40, 'max': 125},
        }
    
    def parse(self, ordering_code: str) -> Optional[OrderingCodeVariant]:
        """
        Parse complete STM32 ordering code
        
        Format: STM32[Family][Series][PartNumber][PinCount][FlashSize][Package][TempRange]
        Example: STM32F405RGT6
        """
        # Normalize
        code = ordering_code.upper().strip()
        
        # Match STM32 ordering code pattern
        pattern = r'STM32([A-Z])(\d{2,3})([A-Z])([A-Z])([A-Z])(\d|Y|3)'
        match = re.match(pattern, code)
        
        if not match:
            return None
        
        family_letter = match.group(1)  # F, L, H, G, W, U, C
        series = match.group(2)  # 405, 103, etc.
        pin_letter = match.group(3)  # R, V, Z, etc.
        flash_letter = match.group(4)  # G, E, C, etc.
        package_letter = match.group(5)  # T, H, Y, etc.
        temp_letter = match.group(6)  # 6, 7, Y, 3
        
        # Decode
        pin_count = self.pin_counts.get(pin_letter, 0)
        flash_kb = self.flash_sizes.get(flash_letter, 0)
        package = self.packages.get(package_letter, 'Unknown')
        temp_info = self.temp_ranges.get(temp_letter, {'range': 'Unknown', 'min': -40, 'max': 85})
        
        # Build family name
        family_map = {
            'F': 'STM32F', 'L': 'STM32L', 'H': 'STM32H', 'G': 'STM32G',
            'W': 'STM32W', 'U': 'STM32U', 'C': 'STM32C', 'M': 'STM32MP'
        }
        family = family_map.get(family_letter, f'STM32{family_letter}')
        
        # Construct part number
        part_number = f"{family_letter}{series}"
        
        return OrderingCodeVariant(
            full_code=code,
            family=family,
            series=series,
            part_number=part_number,
            pin_count=pin_count,
            flash_kb=flash_kb,
            package=package,
            temperature_range=temp_info['range'],
            temperature_min_c=temp_info['min'],
            temperature_max_c=temp_info['max']
        )
    
    def parse_to_dict(self, ordering_code: str) -> Optional[Dict[str, Any]]:
        """Parse and return as dictionary"""
        variant = self.parse(ordering_code)
        if not variant:
            return None
        
        return {
            'full_code': variant.full_code,
            'family': variant.family,
            'series': variant.series,
            'part_number': variant.part_number,
            'pin_count': variant.pin_count,
            'flash_kb': variant.flash_kb,
            'package': variant.package,
            'temperature_range': variant.temperature_range,
            'temperature_min_c': variant.temperature_min_c,
            'temperature_max_c': variant.temperature_max_c,
        }


# Example usage and testing
if __name__ == "__main__":
    parser = OrderingCodeParser()
    
    test_codes = [
        "STM32F405RGT6",
        "STM32F103C8T6",
        "STM32L476RGT6",
        "STM32H743ZIT6",
        "STM32G474RET6",
        "STM32WB55RGV6",
    ]
    
    print("Testing Ordering Code Parser\n")
    print("="*80)
    
    for code in test_codes:
        variant = parser.parse(code)
        if variant:
            print(f"\nCode: {code}")
            print(f"  Family: {variant.family}")
            print(f"  Part Number: {variant.part_number}")
            print(f"  Pin Count: {variant.pin_count}")
            print(f"  Flash: {variant.flash_kb} KB")
            print(f"  Package: {variant.package}")
            print(f"  Temperature: {variant.temperature_range} ({variant.temperature_min_c}°C to {variant.temperature_max_c}°C)")
        else:
            print(f"\nCode: {code} - FAILED TO PARSE")
    
    print("\n" + "="*80)
