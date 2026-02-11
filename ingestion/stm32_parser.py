"""
STM32 Ordering Code Parser

Parses STM32 part numbers to extract specifications.

Example: STM32F405RGT6
- Family: F4
- Line: 05 (performance line)
- Flash: RG = 1024KB
- Package: T = LQFP
- Pins: 6 = 64 pins
- Temp: (default) = -40 to 85°C
"""

from typing import Dict, Optional
import re


class STM32OrderingCodeParser:
    """Parse STM32 part numbers"""
    
    def __init__(self):
        # Flash size codes (common across families)
        self.flash_codes = {
            '4': 16,    # 16KB
            '6': 32,    # 32KB
            '8': 64,    # 64KB
            'B': 128,   # 128KB
            'C': 256,   # 256KB
            'D': 384,   # 384KB
            'E': 512,   # 512KB
            'F': 768,   # 768KB
            'G': 1024,  # 1MB
            'H': 1536,  # 1.5MB
            'I': 2048,  # 2MB
        }
        
        # Package codes
        self.package_codes = {
            'T': 'LQFP',
            'H': 'BGA',
            'U': 'VFQFPN',
            'Y': 'WLCSP',
            'K': 'UFBGA',
            'C': 'LQFP',
            'R': 'LQFP',
            'V': 'LQFP',
            'Z': 'LQFP',
        }
        
        # Pin count codes (last digit)
        self.pin_codes = {
            '4': 16,
            '6': 32,
            '8': 48,
            'B': 48,
            'C': 48,
            'T': 36,
            'U': 63,
            'H': 64,
            'M': 80,
            'R': 64,
            'V': 100,
            'Z': 144,
            'I': 176,
            'N': 216,
        }
        
        # Temperature range (suffix, if present)
        self.temp_codes = {
            '6': (-40, 85),   # Standard
            '7': (-40, 105),  # Extended
            '3': (-40, 125),  # Automotive
        }
    
    def parse(self, mpn: str) -> Dict[str, any]:
        """
        Parse STM32 part number.
        
        Returns dict with: family, line, flash_kb, package, pin_count, temp_min, temp_max
        """
        mpn = mpn.upper().strip()
        
        # Basic validation
        if not mpn.startswith('STM32'):
            return {"error": "Not an STM32 part number"}
        
        # Extract components
        # Format: STM32 F 4 05 R G T 6
        #         ----- - - -- - - - -
        #         Base  | | |  | | | Temp
        #              Fam| |  | | Package
        #                Line  | Flash
        #                     Pins
        
        result = {
            "mpn": mpn,
            "manufacturer": "STMicroelectronics",
        }
        
        # Family (F, L, H, G, etc.)
        if len(mpn) > 5:
            result["family"] = f"STM32{mpn[5]}"
        
        # Line (e.g., 405, 103, 746)
        if len(mpn) > 8:
            result["line"] = mpn[6:9]
        
        # Flash size (e.g., G = 1024KB)
        if len(mpn) > 10:
            flash_code = mpn[10]
            result["flash_kb"] = self.flash_codes.get(flash_code, None)
        
        # Package (e.g., T = LQFP)
        if len(mpn) > 11:
            package_code = mpn[11]
            result["package_family"] = self.package_codes.get(package_code, "Unknown")
        
        # Pin count (last digit before temp)
        if len(mpn) > 12:
            pin_code = mpn[12]
            result["pin_count"] = self.pin_codes.get(pin_code, None)
        
        # Temperature range (optional suffix)
        if len(mpn) > 13:
            temp_code = mpn[13]
            temp_range = self.temp_codes.get(temp_code, (-40, 85))
        else:
            temp_range = (-40, 85)  # Default
        
        result["temp_min_c"] = temp_range[0]
        result["temp_max_c"] = temp_range[1]
        
        # Infer core architecture from family
        family_letter = mpn[5] if len(mpn) > 5 else ''
        result["core"] = self._infer_core(family_letter, result.get("line", ""))
        
        return result
    
    def _infer_core(self, family: str, line: str) -> str:
        """Infer ARM core from family"""
        core_map = {
            'F0': 'Cortex-M0',
            'F1': 'Cortex-M3',
            'F2': 'Cortex-M3',
            'F3': 'Cortex-M4',
            'F4': 'Cortex-M4',
            'F7': 'Cortex-M7',
            'H7': 'Cortex-M7',
            'L0': 'Cortex-M0+',
            'L1': 'Cortex-M3',
            'L4': 'Cortex-M4',
            'L5': 'Cortex-M33',
            'G0': 'Cortex-M0+',
            'G4': 'Cortex-M4',
            'U5': 'Cortex-M33',
            'WB': 'Cortex-M4',
            'WL': 'Cortex-M4',
        }
        
        family_key = f"{family}{line[0] if line else ''}"
        return core_map.get(family_key, f"Cortex-M{family}")


# Example usage
if __name__ == "__main__":
    parser = STM32OrderingCodeParser()
    
    test_parts = [
        "STM32F405RGT6",
        "STM32F103C8T6",
        "STM32H743ZIT6",
        "STM32L476RGT6",
        "STM32F746NGH6",
    ]
    
    print("STM32 Ordering Code Parser Test\n")
    print("="*60)
    
    for mpn in test_parts:
        result = parser.parse(mpn)
        print(f"\n{mpn}:")
        for key, value in result.items():
            if key != "mpn":
                print(f"  {key}: {value}")
