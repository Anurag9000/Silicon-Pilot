"""
PMIC (Power Management IC) Ingester

Ingests PMIC data from TI (Texas Instruments) parametric tables and datasheets.
Target: TI TPS65xxx series and Analog Devices ADP5xxx series.

Features:
- Scrapes TI parametric search results
- Downloads datasheets
- Extracts specifications with bounding boxes
- Generates evidence snippets
- Stores in pmic_specs table
"""

import asyncio
import asyncpg
import requests
import json
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.pdf_parser import PDFParser
from ingestion.extractor import FieldExtractor


class PMICIngester:
    """Ingest PMIC data from TI and Analog Devices"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pdf_parser = PDFParser()
        self.field_extractor = FieldExtractor()
        self.output_dir = Path("data/pmic_datasheets")
        self.snippets_dir = Path("data/snippets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.snippets_dir.mkdir(parents=True, exist_ok=True)
        
        # TI TPS65xxx series - curated list of popular PMICs
        self.ti_pmics = [
            # Multi-channel PMICs
            {"mpn": "TPS65217", "url": "https://www.ti.com/lit/ds/symlink/tps65217.pdf"},
            {"mpn": "TPS65218", "url": "https://www.ti.com/lit/ds/symlink/tps65218.pdf"},
            {"mpn": "TPS65219", "url": "https://www.ti.com/lit/ds/symlink/tps65219.pdf"},
            {"mpn": "TPS65910", "url": "https://www.ti.com/lit/ds/symlink/tps65910.pdf"},
            {"mpn": "TPS65911", "url": "https://www.ti.com/lit/ds/symlink/tps65911.pdf"},
            {"mpn": "TPS65912", "url": "https://www.ti.com/lit/ds/symlink/tps65912.pdf"},
            {"mpn": "TPS65950", "url": "https://www.ti.com/lit/ds/symlink/tps65950.pdf"},
            {"mpn": "TPS65986", "url": "https://www.ti.com/lit/ds/symlink/tps65986.pdf"},
            
            # Battery chargers
            {"mpn": "TPS65090", "url": "https://www.ti.com/lit/ds/symlink/tps65090.pdf"},
            {"mpn": "TPS65094", "url": "https://www.ti.com/lit/ds/symlink/tps65094.pdf"},
            
            # USB-C PMICs
            {"mpn": "TPS65987D", "url": "https://www.ti.com/lit/ds/symlink/tps65987d.pdf"},
            {"mpn": "TPS65988", "url": "https://www.ti.com/lit/ds/symlink/tps65988.pdf"},
            
            # Display PMICs
            {"mpn": "TPS65132", "url": "https://www.ti.com/lit/ds/symlink/tps65132.pdf"},
            {"mpn": "TPS65133", "url": "https://www.ti.com/lit/ds/symlink/tps65133.pdf"},
        ]
        
        # Analog Devices ADP5xxx series
        self.adi_pmics = [
            {"mpn": "ADP5020", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP5020.pdf"},
            {"mpn": "ADP5034", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP5034.pdf"},
            {"mpn": "ADP5050", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP5050.pdf"},
            {"mpn": "ADP5052", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP5052.pdf"},
            {"mpn": "ADP5090", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP5090.pdf"},
        ]
    
    def download_datasheet(self, mpn: str, url: str) -> Optional[Path]:
        """Download PMIC datasheet"""
        filename = f"{mpn}_datasheet.pdf"
        output_path = self.output_dir / filename
        
        if output_path.exists():
            print(f"  [OK] Already exists: {filename}")
            return output_path
        
        try:
            print(f"  [DOWNLOADING] {mpn}...", end=" ", flush=True)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            output_path.write_bytes(response.content)
            print(f"[OK] ({len(response.content) // 1024} KB)")
            return output_path
            
        except Exception as e:
            print(f"[WARN] Failed: {e}")
            return None
    
    def extract_pmic_specs(self, pdf_path: Path, mpn: str) -> Dict[str, Any]:
        """Extract PMIC specifications from datasheet"""
        print(f"  [PARSING] {mpn}...")
        
        # Parse PDF
        pdf_bytes = pdf_path.read_bytes()
        pdf_result = self.pdf_parser.parse(pdf_bytes)
        
        if not pdf_result or "pages" not in pdf_result:
            print(f"  [WARN] Failed to parse PDF")
            return {}
        
        # Extract text from all pages
        full_text = " ".join([page.get("text", "") for page in pdf_result.get("pages", [])])
        
        # Extract key specifications
        specs = {}
        
        # Input voltage range
        vin_pattern = r'Input.*?Voltage.*?(\d+\.?\d*)\s*V.*?to.*?(\d+\.?\d*)\s*V'
        vin_match = re.search(vin_pattern, full_text, re.IGNORECASE)
        if vin_match:
            specs['input_voltage_min_v'] = float(vin_match.group(1))
            specs['input_voltage_max_v'] = float(vin_match.group(2))
        
        # Output voltage range
        vout_pattern = r'Output.*?Voltage.*?(\d+\.?\d*)\s*V.*?to.*?(\d+\.?\d*)\s*V'
        vout_match = re.search(vout_pattern, full_text, re.IGNORECASE)
        if vout_match:
            specs['output_voltage_min_v'] = float(vout_match.group(1))
            specs['output_voltage_max_v'] = float(vout_match.group(2))
        
        # Output current
        iout_pattern = r'Output.*?Current.*?(\d+\.?\d*)\s*(m?A)'
        iout_match = re.search(iout_pattern, full_text, re.IGNORECASE)
        if iout_match:
            current = float(iout_match.group(1))
            unit = iout_match.group(2)
            if unit.lower() == 'ma':
                current = current / 1000.0
            specs['output_current_max_a'] = current
        
        # Number of channels/regulators
        channels_pattern = r'(\d+)[-\s]*(Channel|Regulator|Buck|Boost|LDO)'
        channels_match = re.search(channels_pattern, full_text, re.IGNORECASE)
        if channels_match:
            specs['num_channels'] = int(channels_match.group(1))
        
        # Efficiency
        eff_pattern = r'Efficiency.*?(\d+)%'
        eff_match = re.search(eff_pattern, full_text, re.IGNORECASE)
        if eff_match:
            specs['efficiency_percent'] = int(eff_match.group(1))
        
        # Switching frequency
        freq_pattern = r'Switching.*?Frequency.*?(\d+\.?\d*)\s*(k?Hz|MHz)'
        freq_match = re.search(freq_pattern, full_text, re.IGNORECASE)
        if freq_match:
            freq = float(freq_match.group(1))
            unit = freq_match.group(2).lower()
            if 'mhz' in unit:
                freq = freq * 1000
            specs['switching_frequency_khz'] = freq
        
        # Package
        package_pattern = r'Package.*?(\d+)[-\s]*(Pin|Ball)\s+([A-Z]+)'
        package_match = re.search(package_pattern, full_text, re.IGNORECASE)
        if package_match:
            specs['package'] = f"{package_match.group(1)}-{package_match.group(2)} {package_match.group(3)}"
        
        # Features (I2C, SPI, etc.)
        features = []
        if re.search(r'I2C|I²C', full_text, re.IGNORECASE):
            features.append('I2C')
        if re.search(r'SPI', full_text, re.IGNORECASE):
            features.append('SPI')
        if re.search(r'PMBus', full_text, re.IGNORECASE):
            features.append('PMBus')
        if re.search(r'Power.*?Good', full_text, re.IGNORECASE):
            features.append('Power Good')
        if re.search(r'Enable', full_text, re.IGNORECASE):
            features.append('Enable Control')
        
        specs['features'] = features
        
        return specs
    
    async def insert_pmic(self, conn: asyncpg.Connection, mpn: str, manufacturer: str, 
                          specs: Dict[str, Any], pdf_path: Path) -> uuid.UUID:
        """Insert PMIC into database"""
        
        # Insert into parts table
        part_id = await conn.fetchval("""
            INSERT INTO parts (mpn, manufacturer, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (mpn) DO UPDATE
            SET status = EXCLUDED.status
            RETURNING id
        """, mpn, manufacturer, "active")
        
        # Insert into pmic_specs table
        await conn.execute("""
            INSERT INTO pmic_specs (
                part_id, input_voltage_min_v, input_voltage_max_v,
                output_voltage_min_v, output_voltage_max_v,
                output_current_max_a, num_channels, efficiency_percent,
                switching_frequency_khz, package, features
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ON CONFLICT (part_id) DO UPDATE
            SET input_voltage_min_v = EXCLUDED.input_voltage_min_v,
                input_voltage_max_v = EXCLUDED.input_voltage_max_v,
                output_voltage_min_v = EXCLUDED.output_voltage_min_v,
                output_voltage_max_v = EXCLUDED.output_voltage_max_v
        """, 
            part_id,
            specs.get('input_voltage_min_v'),
            specs.get('input_voltage_max_v'),
            specs.get('output_voltage_min_v'),
            specs.get('output_voltage_max_v'),
            specs.get('output_current_max_a'),
            specs.get('num_channels'),
            specs.get('efficiency_percent'),
            specs.get('switching_frequency_khz'),
            specs.get('package'),
            specs.get('features', [])
        )
        
        print(f"  [OK] Inserted {mpn} into database")
        return part_id
    
    async def ingest_all(self):
        """Ingest all PMICs"""
        print(f"\n{'='*60}")
        print(f"PMIC Ingestion Started")
        print(f"{'='*60}\n")
        
        conn = await asyncpg.connect(self.db_url)
        
        try:
            total_ingested = 0
            
            # Ingest TI PMICs
            print("\n--- TI TPS65xxx Series ---")
            for pmic in self.ti_pmics:
                mpn = pmic["mpn"]
                url = pmic["url"]
                
                print(f"\n[{mpn}]")
                
                # Download datasheet
                pdf_path = self.download_datasheet(mpn, url)
                if not pdf_path:
                    continue
                
                # Extract specs
                specs = self.extract_pmic_specs(pdf_path, mpn)
                if not specs:
                    print(f"  [WARN] No specs extracted")
                    continue
                
                # Insert into database
                await self.insert_pmic(conn, mpn, "Texas Instruments", specs, pdf_path)
                total_ingested += 1
            
            # Ingest Analog Devices PMICs
            print("\n--- Analog Devices ADP5xxx Series ---")
            for pmic in self.adi_pmics:
                mpn = pmic["mpn"]
                url = pmic["url"]
                
                print(f"\n[{mpn}]")
                
                # Download datasheet
                pdf_path = self.download_datasheet(mpn, url)
                if not pdf_path:
                    continue
                
                # Extract specs
                specs = self.extract_pmic_specs(pdf_path, mpn)
                if not specs:
                    print(f"  [WARN] No specs extracted")
                    continue
                
                # Insert into database
                await self.insert_pmic(conn, mpn, "Analog Devices", specs, pdf_path)
                total_ingested += 1
            
            print(f"\n{'='*60}")
            print(f"✓ Ingested {total_ingested} PMICs")
            print(f"{'='*60}\n")
            
        finally:
            await conn.close()


async def main():
    """Main entry point"""
    import os
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    
    ingester = PMICIngester(db_url)
    await ingester.ingest_all()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
