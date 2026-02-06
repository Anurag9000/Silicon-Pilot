"""
Field Extractor

Extract MCU specifications from parsed PDF data with evidence tracking.
Handles vendor-specific patterns and part number decoding.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from core.models import EvidenceRecord

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extract structured fields from parsed PDF data"""
    
    def __init__(self):
        """Initialize field extractor with patterns"""
        self.mpn_patterns = self._init_mpn_patterns()
        self.field_patterns = self._init_field_patterns()
    
    def _init_mpn_patterns(self) -> Dict[str, List[str]]:
        """Initialize manufacturer part number patterns"""
        return {
            'STMicroelectronics': [
                r'STM32[A-Z]\d+[A-Z]{1,3}\d*',
                r'STM8[A-Z]\d+[A-Z]{1,3}\d*',
            ],
            'Espressif': [
                r'ESP32-[A-Z]\d+',
                r'ESP32[A-Z]\d*',
                r'ESP8266',
            ],
            'Nordic': [
                r'nRF\d{5}',
                r'nRF52\d{3}',
            ],
            'Microchip': [
                r'ATSAM[A-Z]\d+[A-Z]\d+',
                r'ATSAMD\d+[A-Z]\d+',
                r'PIC\d{2}[A-Z]\d+',
            ],
            'Texas Instruments': [
                r'MSP430[A-Z]{2}\d+',
                r'TM4C\d+[A-Z]+',
            ],
            'Raspberry Pi': [
                r'RP20\d{2}',
            ],
        }
    
    def _init_field_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize field extraction patterns"""
        return {
            'flash_kb': [
                {'pattern': r'(\d+)\s*[KM]B?\s+Flash', 'unit_multiplier': {'K': 1, 'M': 1024}},
                {'pattern': r'Flash.*?(\d+)\s*[KM]B?', 'unit_multiplier': {'K': 1, 'M': 1024}},
                {'pattern': r'Program\s+Memory.*?(\d+)\s*[KM]B?', 'unit_multiplier': {'K': 1, 'M': 1024}},
            ],
            'sram_kb': [
                {'pattern': r'(\d+)\s*[KM]B?\s+(?:SRAM|RAM)', 'unit_multiplier': {'K': 1, 'M': 1024}},
                {'pattern': r'(?:SRAM|RAM).*?(\d+)\s*[KM]B?', 'unit_multiplier': {'K': 1, 'M': 1024}},
            ],
            'max_mhz': [
                {'pattern': r'(\d+)\s*MHz', 'unit_multiplier': None},
                {'pattern': r'Clock.*?(\d+)\s*MHz', 'unit_multiplier': None},
                {'pattern': r'Frequency.*?(\d+)\s*MHz', 'unit_multiplier': None},
            ],
            'temp_min_c': [
                {'pattern': r'(-?\d+)°?C?\s+to\s+\d+°?C', 'unit_multiplier': None},
                {'pattern': r'Operating.*?(-?\d+)°?C', 'unit_multiplier': None},
            ],
            'temp_max_c': [
                {'pattern': r'-?\d+°?C?\s+to\s+(\d+)°?C', 'unit_multiplier': None},
                {'pattern': r'Operating.*?to\s+(\d+)°?C', 'unit_multiplier': None},
            ],
            'package': [
                {'pattern': r'(LQFP|QFN|BGA|TQFP|WLCSP|SOIC|DIP)[-\s]?\d*', 'unit_multiplier': None},
            ],
            'pin_count': [
                {'pattern': r'(\d+)[-\s]?pin', 'unit_multiplier': None},
                {'pattern': r'(?:LQFP|QFN|BGA|TQFP)[-\s]?(\d+)', 'unit_multiplier': None},
            ],
            'vdd_min_v': [
                {'pattern': r'(\d+\.?\d*)\s*V\s+to\s+\d+\.?\d*\s*V', 'unit_multiplier': None},
                {'pattern': r'Voltage.*?(\d+\.?\d*)\s*V', 'unit_multiplier': None},
            ],
            'vdd_max_v': [
                {'pattern': r'\d+\.?\d*\s*V\s+to\s+(\d+\.?\d*)\s*V', 'unit_multiplier': None},
                {'pattern': r'Voltage.*?to\s+(\d+\.?\d*)\s*V', 'unit_multiplier': None},
            ],
            'power_run_ua_mhz': [
                {'pattern': r'(\d+\.?\d*)\s*µA/MHz', 'unit_multiplier': None},
                {'pattern': r'Run\s+mode.*?(\d+\.?\d*)\s*µA/MHz', 'unit_multiplier': None},
            ],
            'power_stop_ua': [
                {'pattern': r'(\d+\.?\d*)\s*µA\s+in\s+Stop', 'unit_multiplier': None},
                {'pattern': r'Stop\s+mode.*?(\d+\.?\d*)\s*µA', 'unit_multiplier': None},
            ],
            'power_standby_na': [
                {'pattern': r'(\d+\.?\d*)\s*nA\s+in\s+Standby', 'unit_multiplier': None},
                {'pattern': r'Standby\s+mode.*?(\d+\.?\d*)\s*nA', 'unit_multiplier': None},
            ],
        }
    
    def extract_mpns(
        self,
        text: str,
        manufacturer: Optional[str] = None,
    ) -> List[str]:
        """
        Extract manufacturer part numbers from text.
        
        Args:
            text: Text to search
            manufacturer: Manufacturer name (for targeted patterns)
        
        Returns:
            List of found MPNs
        """
        mpns = set()
        
        # If manufacturer specified, use targeted patterns
        if manufacturer and manufacturer in self.mpn_patterns:
            patterns = self.mpn_patterns[manufacturer]
        else:
            # Use all patterns
            patterns = [p for patterns in self.mpn_patterns.values() for p in patterns]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            mpns.update(matches)
        
        return list(mpns)
    
    def extract_field(
        self,
        field_name: str,
        text: str,
        page_num: int,
        bbox: Optional[Tuple[float, float, float, float]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract a specific field from text.
        
        Args:
            field_name: Field to extract (e.g., 'flash_kb')
            text: Text to search
            page_num: Page number
            bbox: Bounding box of text
        
        Returns:
            Dict with extracted value and metadata, or None
        """
        if field_name not in self.field_patterns:
            logger.warning(f"No patterns defined for field: {field_name}")
            return None
        
        patterns = self.field_patterns[field_name]
        
        for pattern_def in patterns:
            pattern = pattern_def['pattern']
            unit_multiplier = pattern_def.get('unit_multiplier')
            
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                raw_value = match.group(1)
                
                # Apply unit conversion if needed
                if unit_multiplier:
                    # Extract unit from match
                    unit_match = re.search(r'[KM]B?', match.group(0), re.IGNORECASE)
                    if unit_match:
                        unit = unit_match.group(0)[0].upper()
                        multiplier = unit_multiplier.get(unit, 1)
                        normalized_value = int(raw_value) * multiplier
                    else:
                        normalized_value = int(raw_value)
                else:
                    normalized_value = int(raw_value)
                
                return {
                    'field_name': field_name,
                    'raw_value': match.group(0),
                    'normalized_value': normalized_value,
                    'page': page_num,
                    'bbox': bbox,
                    'pattern_used': pattern,
                }
        
        return None
    
    def extract_from_table(
        self,
        table: Dict,
        field_mapping: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Extract fields from a table.
        
        Args:
            table: Table data from PDF parser
            field_mapping: Map of field names to possible column headers
        
        Returns:
            List of extracted field data
        """
        extractions = []
        
        # Get table data
        data = table.get('data', [])
        if not data:
            return extractions
        
        # Find relevant columns
        headers = list(data[0].keys()) if data else []
        
        for field_name, possible_headers in field_mapping.items():
            for header in headers:
                if any(ph.lower() in header.lower() for ph in possible_headers):
                    # Extract values from this column
                    for row in data:
                        value = row.get(header)
                        if value and str(value).strip():
                            extractions.append({
                                'field_name': field_name,
                                'raw_value': str(value),
                                'normalized_value': self._normalize_value(field_name, str(value)),
                                'page': table['page'],
                                'bbox': table.get('bbox'),
                                'source': 'table',
                            })
                    break
        
        return extractions
    
    def _normalize_value(self, field_name: str, raw_value: str) -> Any:
        """Normalize a raw value based on field type"""
        # Remove common noise
        cleaned = re.sub(r'[^\d.KMG-]', '', raw_value, flags=re.IGNORECASE)
        
        # Handle numeric fields
        if field_name in ['flash_kb', 'sram_kb', 'max_mhz', 'pin_count']:
            # Extract number and unit
            match = re.match(r'([\d.]+)([KMG])?', cleaned, re.IGNORECASE)
            if match:
                number = float(match.group(1))
                unit = match.group(2)
                
                # Apply multiplier
                multipliers = {'K': 1, 'M': 1024, 'G': 1024*1024}
                if unit:
                    number *= multipliers.get(unit.upper(), 1)
                
                return int(number)
        
        elif field_name in ['temp_min_c', 'temp_max_c']:
            # Extract temperature
            match = re.search(r'-?\d+', cleaned)
            if match:
                return int(match.group(0))
        
        # Default: return cleaned string
        return cleaned
    
    def extract_peripherals(
        self,
        text: str,
        page_num: int,
    ) -> Dict[str, int]:
        """
        Extract peripheral counts from text.
        
        Returns:
            Dict of peripheral_name -> count
        """
        peripherals = {}
        
        peripheral_patterns = {
            'can_count': [r'(\d+)\s*×?\s*CAN', r'CAN\s*×?\s*(\d+)'],
            'can_fd_count': [r'(\d+)\s*×?\s*CAN-?FD', r'CAN-?FD\s*×?\s*(\d+)'],
            'uart_count': [r'(\d+)\s*×?\s*U?ART', r'U?ART\s*×?\s*(\d+)'],
            'spi_count': [r'(\d+)\s*×?\s*SPI', r'SPI\s*×?\s*(\d+)'],
            'i2c_count': [r'(\d+)\s*×?\s*I[²2]C', r'I[²2]C\s*×?\s*(\d+)'],
            'adc_channels': [r'(\d+)[-\s]?channel\s+ADC', r'ADC.*?(\d+)[-\s]?channel'],
            'timers_count': [r'(\d+)\s*×?\s*timer', r'timer\s*×?\s*(\d+)'],
        }
        
        for peripheral, patterns in peripheral_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    peripherals[peripheral] = int(match.group(1))
                    break
        
        # Boolean peripherals
        if re.search(r'USB\s+(Full[-\s]?Speed|FS)', text, re.IGNORECASE):
            peripherals['usb_fs'] = True
        if re.search(r'USB\s+(High[-\s]?Speed|HS)', text, re.IGNORECASE):
            peripherals['usb_hs'] = True
        if re.search(r'Ethernet|ETH', text, re.IGNORECASE):
            peripherals['ethernet'] = True
        
        return peripherals
