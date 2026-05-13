
"""
STM32 Datasheet Extractor

Extracts detailed tables from STM32 datasheets:
1. Pin Definitions (Pin Name, Alternate Functions, Additional Functions)
2. Power Consumption (Run, Sleep, Stop, Standby currents)

Uses pdfplumber for table extraction with targeted page identification.
"""

import pdfplumber
import re
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PinDefinition:
    pin_name: str
    pin_number: int  # TBD: Handling multiple packages where pin number varies
    type: str
    io_structure: str
    alternate_functions: List[str]
    additional_functions: List[str]

@dataclass
class PowerModeData:
    mode: str
    conditions: str
    typ_current_ua: float
    max_current_ua: float

class STM32DatasheetExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
    
    def extract_pin_definitions(self) -> List[Dict[str, Any]]:
        """
        Extracts the 'Pin and ball definitions' or 'Alternate function mapping' tables.
        """
        results = []
        with pdfplumber.open(self.pdf_path) as pdf:
            # 1. Find pages with "Pin definition" in title
            relevant_pages = [] 
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and ("Pin definition" in text or "Alternate function mapping" in text):
                    relevant_pages.append(i)
            
            print(f"Found {len(relevant_pages)} potential pin definition pages.")
            
            # 2. Extract tables from these pages
            for page_idx in relevant_pages:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()
                
                for table in tables:
                    # Heuristic: Check headers for "Pin name" and "Alternate functions"
                    if not table or len(table) < 2: continue
                    
                    headers = [str(h).lower().replace('\n', ' ') for h in table[0] if h]
                    if "pin name" in headers or "alternate function" in "".join(headers):
                        print(f"Processing table on page {page_idx+1}...")
                        results.extend(self._process_pin_table(table))
                        
        return results

    def _process_pin_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        # This requires careful normalization of headers
        # For now, simplistic extraction
        data = []
        headers = table[0]
        
        # Try to find column indices
        name_idx = -1
        af_idx = -1
        
        for i, h in enumerate(headers):
            if h and "Pin name" in h: name_idx = i
            if h and "Alternate function" in h: af_idx = i
            
        if name_idx == -1: return []
        
        for row in table[1:]:
            if len(row) <= name_idx: continue
            pin_name = row[name_idx]
            if not pin_name or not pin_name.strip(): continue
            
            # Clean pin name (remove split lines)
            pin_name = pin_name.replace('\n', '').strip()
            
            # Basic pin name validation (e.g. PA0, PB12)
            if not re.match(r'P[A-K]\d+', pin_name): continue
            
            entry = {
                "pin_name": pin_name,
                "af_functions": []
            }
            
            if af_idx != -1 and len(row) > af_idx:
                afs = row[af_idx]
                if afs:
                    # Split by comma or newline
                    entry["af_functions"] = [f.strip() for f in re.split(r'[,\n]', afs) if f.strip()]
            
            data.append(entry)
            
        return data


    def extract_power_modes(self) -> List[Dict[str, Any]]:
        """
        Extracts 'Current consumption' tables for Run, Sleep, Stop, Standby.
        """
        results = []
        with pdfplumber.open(self.pdf_path) as pdf:
            relevant_pages = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and ("Current consumption" in text or "Operating conditions" in text):
                    # Look for specific mode keywords in the same page or nearby
                    relevant_pages.append(i)
            
            print(f"Found {len(relevant_pages)} potential power pages.")
            
            for page_idx in relevant_pages:
                page = pdf.pages[page_idx]
                # specific settings for whitespace-defined tables
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                }
                tables = page.extract_tables(table_settings)
            for page_idx in relevant_pages:
                page = pdf.pages[page_idx]
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2: continue
                    headers = [str(h).lower().replace('\n', ' ') for h in table[0] if h]
                    
                    # Heuristic for Power Table
                    if any(x in " ".join(headers) for x in ["conditions", "typ", "max", "unit"]):
                        results.extend(self._process_power_table(table))
        return results

    def extract_peripheral_counts(self) -> Dict[str, int]:
        """
        Extracts peripheral counts (SPI, I2C, UART, etc.) from the 'Features' section (usually Page 1).
        """
        counts = {
            "spi_count": 0,
            "i2c_count": 0,
            "uart_count": 0,
            "can_count": 0,
            "usb_fs": 0,
            "adc_channels": 0,
            "dac_channels": 0
        }
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Check first 3 pages for Features list
            text = ""
            for i in range(min(3, len(pdf.pages))):
                page_text = pdf.pages[i].extract_text() or ""
                text += page_text
                
        # Regex patterns
        # Look for "3x SPI", "3 x SPI", "up to 3 SPI"
        patterns = {
            "spi_count": [r"(\d+)\s*[xX]?\s*SPI", r"up to (\d+)\s*SPI"],
            "i2c_count": [r"(\d+)\s*[xX]?\s*I2C", r"up to (\d+)\s*I2C"],
            "uart_count": [r"(\d+)\s*[xX]?\s*U(S)ART", r"up to (\d+)\s*U(S)ART"],
            "can_count": [r"(\d+)\s*[xX]?\s*CAN", r"up to (\d+)\s*CAN"],
            "adc_channels": [r"(\d+)\s*x\s*12-bit ADC", r"(\d+)\s*channels"], # Simplified
            "dac_channels": [r"(\d+)\s*[xX]?\s*DAC"],
        }
        
        for key, regex_list in patterns.items():
            for pattern in regex_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        # Handle groups (some regex has groups implies tuple return)
                        val = match if isinstance(match, str) else match[0]
                        count = int(val)
                        # Keep the max found (e.g. if it sees "3x SPI" and later "SPI1, SPI2", regex might match 3)
                        if count > counts[key]:
                            counts[key] = count
                    except Exception:
                        pass
        
        # USB special case
        if "USB 2.0 full-speed" in text or "USB FS" in text:
            counts["usb_fs"] = 1
            
        return counts

    def _process_power_table(self, table: List[List[str]]) -> List[Dict[str, Any]]:
        # Simplified parser for now
        data = []
        if not table or not table[0]: return []
        
        headers = [str(h).lower() for h in table[0] if h]
        print(f"DEBUG: Power Table Headers: {headers}")
        
        # Find ID columns
        mode_idx = -1
        typ_idx = -1
        max_idx = -1
        
        for i, h in enumerate(headers):
            if "mode" in h: mode_idx = i
            if "typ" in h: typ_idx = i
            if "max" in h: max_idx = i
            
        print(f"DEBUG: Indices - Mode:{mode_idx}, Typ:{typ_idx}, Max:{max_idx}")
            
        if typ_idx == -1: 
            print("DEBUG: Typ column not found.")
            return []
        
        for row in table[1:]:
            # Handle row length mismatch if pdfplumber merges cells weirdly
            if len(row) <= typ_idx: continue
            
            # Extract Mode (often in the first column or merged)
            mode = "Run" # Default fallback
            if mode_idx != -1 and mode_idx < len(row) and row[mode_idx]:
                mode = row[mode_idx].replace('\n', ' ').strip()
            
            # Extract basic current (assuming uA or mA depending on context - logic needed)
            # For now, just extracting raw numbers
            try:
                val_str = row[typ_idx]
                if not val_str: continue
                match = re.search(r'\d+\.?\d*', val_str)
                if not match: continue
                
                val = float(match.group())
                
                # Check unit in header or row? Assuming uA for now if < 1000, else mA? 
                # Real datasheets specify unit in a separate column or header.
                # HARDCODED assumption for mock: uA
                
                entry = {
                    "mode": mode,
                    "conditions": "",
                    "typ_current_ua": val,
                    "max_current_ua": val * 1.2 # Placeholder
                }
                data.append(entry)
            except Exception as e:
                print(f"DEBUG: parsing error row {row}: {e}")
                continue
                
        return data

    async def save_to_db(self, conn, part_id: str):
        # Save Pins
        pins = self.extract_pin_definitions()
        print(f"Saving {len(pins)} pins to DB for part {part_id}")
        
        # Clear existing
        await conn.execute("DELETE FROM mcu_pin_functions WHERE part_id = $1", part_id)
        
        for pin_num, p in enumerate(pins, start=1):
            # Distribute AFs into af0_function...af15_function
            afs = p['af_functions'] if p['af_functions'] else []
            # Pad with None up to 16
            af_cols = afs[:16] + [None] * (16 - len(afs[:16]))
            
            await conn.execute("""
                INSERT INTO mcu_pin_functions (
                    part_id, pin_number, pin_name, 
                    af0_function, af1_function, af2_function, af3_function,
                    af4_function, af5_function, af6_function, af7_function,
                    af8_function, af9_function, af10_function, af11_function,
                    af12_function, af13_function, af14_function, af15_function
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
            """, part_id, pin_num, p['pin_name'], *af_cols)
            
        # Save Power
        power = self.extract_power_modes()
        print(f"Saving {len(power)} power modes to DB for part {part_id}")
        
        await conn.execute("DELETE FROM power_modes WHERE part_id = $1", part_id)
        
        for p in power:
            await conn.execute("""
                INSERT INTO power_modes (
                    part_id, mode_name, voltage_v, current_typ_ua, current_max_ua
                ) VALUES ($1, $2, $3, $4, $5)
            """, part_id, p['mode'], 3.3, p['typ_current_ua'], p['max_current_ua'])
            
        # Save Peripherals
        specs = self.extract_peripheral_counts()
        print(f"Updating specs for {part_id}: {specs}")
        await conn.execute("""
            UPDATE mcu_specs
            SET spi_count = $1, i2c_count = $2, uart_count = $3, 
                can_count = $4, usb_fs = $5, dac_channels = $6
            WHERE part_id = $7
        """, specs['spi_count'], specs['i2c_count'], specs['uart_count'], 
             specs['can_count'], specs['usb_fs'], specs['dac_channels'],
             part_id)

if __name__ == "__main__":
    # Test run
    import sys
    import asyncio
    
    path = "d:/Done,Toreview/Silicon-Pilot/datasheets/mock_stm32.pdf"
    if len(sys.argv) > 1: path = sys.argv[1]
    
    extractor = STM32DatasheetExtractor(path)
    pins = extractor.extract_pin_definitions()
    print(f"Extracted {len(pins)} pin definitions.")
    
    power = extractor.extract_power_modes()
    print(f"Extracted {len(power)} power modes.")
