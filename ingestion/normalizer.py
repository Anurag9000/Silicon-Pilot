"""
Normalizer

Normalize extracted values: unit conversion, package family mapping,
synonym resolution, and part-number suffix decoding.
"""

import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalize extracted field values"""
    
    def __init__(self):
        """Initialize normalizer with mapping tables"""
        self.package_family_map = self._init_package_family_map()
        self.synonym_map = self._init_synonym_map()
        self.vendor_suffix_decoders = self._init_suffix_decoders()
    
    def _init_package_family_map(self) -> Dict[str, str]:
        """Map package variants to families"""
        return {
            # QFP variants
            'LQFP': 'QFP',
            'TQFP': 'QFP',
            'PQFP': 'QFP',
            'HQFP': 'QFP',
            'VQFP': 'QFP',
            'QFP': 'QFP',
            
            # QFN variants
            'QFN': 'QFN',
            'VQFN': 'QFN',
            'HVQFN': 'QFN',
            'UQFN': 'QFN',
            'WQFN': 'QFN',
            
            # BGA variants
            'BGA': 'BGA',
            'FBGA': 'BGA',
            'TFBGA': 'BGA',
            'UFBGA': 'BGA',
            'WLCSP': 'BGA',  # Wafer-level chip-scale package
            
            # Others
            'SOIC': 'SOIC',
            'TSSOP': 'SOIC',
            'SSOP': 'SOIC',
            'DIP': 'DIP',
            'PDIP': 'DIP',
        }
    
    def _init_synonym_map(self) -> Dict[str, Dict[str, str]]:
        """Map synonyms to canonical names"""
        return {
            'peripherals': {
                'CAN': 'CAN',
                'CAN 2.0': 'CAN',
                'CAN2.0': 'CAN',
                'CAN-FD': 'CAN_FD',
                'CANFD': 'CAN_FD',
                'M_CAN': 'CAN_FD',
                'USART': 'UART',
                'UART': 'UART',
                'I2C': 'I2C',
                'I²C': 'I2C',
                'IIC': 'I2C',
                'TWI': 'I2C',  # Two-Wire Interface (Atmel)
            },
            'cores': {
                'ARM Cortex-M0': 'ARM Cortex-M0',
                'Cortex-M0': 'ARM Cortex-M0',
                'CM0': 'ARM Cortex-M0',
                'ARM Cortex-M0+': 'ARM Cortex-M0+',
                'Cortex-M0+': 'ARM Cortex-M0+',
                'CM0+': 'ARM Cortex-M0+',
                'ARM Cortex-M3': 'ARM Cortex-M3',
                'Cortex-M3': 'ARM Cortex-M3',
                'CM3': 'ARM Cortex-M3',
                'ARM Cortex-M4': 'ARM Cortex-M4',
                'Cortex-M4': 'ARM Cortex-M4',
                'CM4': 'ARM Cortex-M4',
                'ARM Cortex-M7': 'ARM Cortex-M7',
                'Cortex-M7': 'ARM Cortex-M7',
                'CM7': 'ARM Cortex-M7',
                'ARM Cortex-M33': 'ARM Cortex-M33',
                'Cortex-M33': 'ARM Cortex-M33',
                'CM33': 'ARM Cortex-M33',
            },
        }
    
    def _init_suffix_decoders(self) -> Dict[str, callable]:
        """Initialize part-number suffix decoders per vendor"""
        return {
            'STMicroelectronics': self._decode_stm32_suffix,
            'Espressif': self._decode_esp32_suffix,
            'Nordic': self._decode_nrf_suffix,
        }
    
    def normalize_package(self, package_name: str) -> Dict[str, str]:
        """
        Normalize package name to family.
        
        Args:
            package_name: Raw package name (e.g., "LQFP-64")
        
        Returns:
            Dict with package_family and package_name
        """
        # Extract base package type
        match = re.match(r'([A-Z]+)', package_name.upper())
        if match:
            base_type = match.group(1)
            family = self.package_family_map.get(base_type, base_type)
            
            return {
                'package_family': family,
                'package_name': package_name.upper(),
            }
        
        return {
            'package_family': 'UNKNOWN',
            'package_name': package_name.upper(),
        }
    
    def normalize_peripheral(self, peripheral_name: str) -> str:
        """Normalize peripheral name using synonym map"""
        peripheral_map = self.synonym_map.get('peripherals', {})
        return peripheral_map.get(peripheral_name.upper(), peripheral_name.upper())
    
    def normalize_core(self, core_name: str) -> str:
        """Normalize core architecture name"""
        core_map = self.synonym_map.get('cores', {})
        
        # Try exact match first
        if core_name in core_map:
            return core_map[core_name]
        
        # Try case-insensitive match
        for key, value in core_map.items():
            if key.lower() == core_name.lower():
                return value
        
        return core_name
    
    def normalize_temperature(self, temp_str: str) -> Optional[int]:
        """
        Normalize temperature string to integer Celsius.
        
        Args:
            temp_str: Temperature string (e.g., "-40°C", "85C", "-40")
        
        Returns:
            Temperature in Celsius
        """
        # Remove units and extract number
        cleaned = re.sub(r'[°CF]', '', temp_str)
        match = re.search(r'-?\d+', cleaned)
        
        if match:
            return int(match.group(0))
        
        return None
    
    def normalize_memory(self, memory_str: str, field_name: str) -> Optional[int]:
        """
        Normalize memory value to KB.
        
        Args:
            memory_str: Memory string (e.g., "512KB", "1MB", "2M")
            field_name: Field name for context
        
        Returns:
            Memory in KB
        """
        # Extract number and unit
        match = re.match(r'([\d.]+)\s*([KMG])?B?', memory_str.upper())
        
        if match:
            number = float(match.group(1))
            unit = match.group(2)
            
            # Convert to KB
            multipliers = {'K': 1, 'M': 1024, 'G': 1024*1024}
            if unit:
                number *= multipliers.get(unit, 1)
            
            return int(number)
        
        return None
    
    def decode_part_number(
        self,
        mpn: str,
        manufacturer: str,
    ) -> Dict[str, Any]:
        """
        Decode part number suffix to extract encoded information.
        
        Args:
            mpn: Manufacturer part number
            manufacturer: Manufacturer name
        
        Returns:
            Dict with decoded fields (flash_kb, package, temp_grade, etc.)
        """
        decoder = self.vendor_suffix_decoders.get(manufacturer)
        
        if decoder:
            return decoder(mpn)
        
        return {}
    
    def _decode_stm32_suffix(self, mpn: str) -> Dict[str, Any]:
        """
        Decode STM32 part number suffix.
        
        Example: STM32F405RGT6
        - F4: Family
        - 05: Sub-family
        - R: Pin count (64)
        - G: Flash size (1024KB)
        - T: Package (LQFP)
        - 6: Temperature range (-40 to 85°C)
        """
        decoded = {}
        
        # Extract components
        match = re.match(r'STM32([A-Z])(\d{2})([A-Z])([A-Z])([A-Z])(\d)', mpn)
        
        if match:
            family, subfamily, pins, flash, package, temp = match.groups()
            
            # Pin count mapping
            pin_map = {
                'C': 48, 'R': 64, 'V': 100, 'Z': 144, 'I': 176, 'B': 208,
            }
            decoded['pin_count'] = pin_map.get(pins)
            
            # Flash size mapping (KB)
            flash_map = {
                '4': 16, '6': 32, '8': 64, 'B': 128, 'C': 256,
                'D': 384, 'E': 512, 'F': 768, 'G': 1024, 'H': 1536,
                'I': 2048,
            }
            decoded['flash_kb'] = flash_map.get(flash)
            
            # Package mapping
            package_map = {
                'T': 'LQFP', 'H': 'BGA', 'U': 'UFQFPN', 'Y': 'WLCSP',
            }
            decoded['package_name'] = package_map.get(package)
            
            # Temperature range mapping
            temp_map = {
                '6': (-40, 85),
                '7': (-40, 105),
                '3': (-40, 125),
            }
            temp_range = temp_map.get(temp)
            if temp_range:
                decoded['temp_min_c'], decoded['temp_max_c'] = temp_range
        
        return decoded
    
    def _decode_esp32_suffix(self, mpn: str) -> Dict[str, Any]:
        """
        Decode ESP32 part number.
        
        Example: ESP32-S3
        - S3: Variant (Xtensa LX7, WiFi + BLE)
        """
        decoded = {}
        
        if 'ESP32-S3' in mpn:
            decoded['core'] = 'Xtensa LX7'
            decoded['has_wireless'] = True
        elif 'ESP32-S2' in mpn:
            decoded['core'] = 'Xtensa LX7'
            decoded['has_wireless'] = True
        elif 'ESP32-C3' in mpn:
            decoded['core'] = 'RISC-V'
            decoded['has_wireless'] = True
        elif 'ESP32' in mpn:
            decoded['core'] = 'Xtensa LX6'
            decoded['has_wireless'] = True
        
        return decoded
    
    def _decode_nrf_suffix(self, mpn: str) -> Dict[str, Any]:
        """
        Decode Nordic nRF part number.
        
        Example: nRF52840
        - 52: Series
        - 840: Variant (flash, peripherals)
        """
        decoded = {}
        
        if 'nRF52840' in mpn:
            decoded['flash_kb'] = 1024
            decoded['sram_kb'] = 256
            decoded['has_wireless'] = True
        elif 'nRF52832' in mpn:
            decoded['flash_kb'] = 512
            decoded['sram_kb'] = 64
            decoded['has_wireless'] = True
        
        return decoded
