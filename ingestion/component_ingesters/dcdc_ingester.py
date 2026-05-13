"""
DC-DC Converter Ingester

Ingests DC-DC converter data from TI TPS62xxx series and Linear Tech LT3xxx series.

Features:
- Downloads datasheets
- Extracts buck/boost converter specifications
- Stores in dcdc_specs table
"""

import asyncio
import asyncpg
import requests
import json
import uuid
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.pdf_parser import PDFParser


class DCDCIngester:
    """Ingest DC-DC converter data"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pdf_parser = PDFParser()
        self.output_dir = Path("data/dcdc_datasheets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # TI TPS62xxx series (Buck converters)
        self.ti_dcdc = [
            {"mpn": "TPS62050", "url": "https://www.ti.com/lit/ds/symlink/tps62050.pdf", "topology": "buck"},
            {"mpn": "TPS62056", "url": "https://www.ti.com/lit/ds/symlink/tps62056.pdf", "topology": "buck"},
            {"mpn": "TPS62060", "url": "https://www.ti.com/lit/ds/symlink/tps62060.pdf", "topology": "buck"},
            {"mpn": "TPS62090", "url": "https://www.ti.com/lit/ds/symlink/tps62090.pdf", "topology": "buck"},
            {"mpn": "TPS62130", "url": "https://www.ti.com/lit/ds/symlink/tps62130.pdf", "topology": "buck"},
            {"mpn": "TPS62160", "url": "https://www.ti.com/lit/ds/symlink/tps62160.pdf", "topology": "buck"},
            {"mpn": "TPS62170", "url": "https://www.ti.com/lit/ds/symlink/tps62170.pdf", "topology": "buck"},
            {"mpn": "TPS62200", "url": "https://www.ti.com/lit/ds/symlink/tps62200.pdf", "topology": "buck"},
            {"mpn": "TPS62230", "url": "https://www.ti.com/lit/ds/symlink/tps62230.pdf", "topology": "buck"},
            {"mpn": "TPS62260", "url": "https://www.ti.com/lit/ds/symlink/tps62260.pdf", "topology": "buck"},
            {"mpn": "TPS62290", "url": "https://www.ti.com/lit/ds/symlink/tps62290.pdf", "topology": "buck"},
            {"mpn": "TPS62400", "url": "https://www.ti.com/lit/ds/symlink/tps62400.pdf", "topology": "buck"},
            {"mpn": "TPS62420", "url": "https://www.ti.com/lit/ds/symlink/tps62420.pdf", "topology": "buck"},
            {"mpn": "TPS62480", "url": "https://www.ti.com/lit/ds/symlink/tps62480.pdf", "topology": "buck"},
            {"mpn": "TPS62560", "url": "https://www.ti.com/lit/ds/symlink/tps62560.pdf", "topology": "buck"},
            {"mpn": "TPS62730", "url": "https://www.ti.com/lit/ds/symlink/tps62730.pdf", "topology": "buck"},
            {"mpn": "TPS62810", "url": "https://www.ti.com/lit/ds/symlink/tps62810.pdf", "topology": "buck"},
            {"mpn": "TPS62840", "url": "https://www.ti.com/lit/ds/symlink/tps62840.pdf", "topology": "buck"},
            {"mpn": "TPS62870", "url": "https://www.ti.com/lit/ds/symlink/tps62870.pdf", "topology": "buck"},
            {"mpn": "TPS62902", "url": "https://www.ti.com/lit/ds/symlink/tps62902.pdf", "topology": "buck"},
        ]
        
        # Linear Tech LT3xxx series
        self.lt_dcdc = [
            {"mpn": "LT3045", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3045fa.pdf", "topology": "ldo"},
            {"mpn": "LT3080", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3080fc.pdf", "topology": "ldo"},
            {"mpn": "LT3430", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3430fc.pdf", "topology": "buck"},
            {"mpn": "LT3502", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3502fc.pdf", "topology": "buck"},
            {"mpn": "LT3580", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3580fc.pdf", "topology": "boost"},
            {"mpn": "LT3652", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3652fc.pdf", "topology": "buck"},
            {"mpn": "LT3755", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3755fc.pdf", "topology": "buck-boost"},
            {"mpn": "LT3791", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3791fc.pdf", "topology": "buck-boost"},
            {"mpn": "LT3922", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3922fc.pdf", "topology": "buck"},
            {"mpn": "LT3956", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/3956fc.pdf", "topology": "buck-boost"},
        ]
    
    def download_datasheet(self, mpn: str, url: str) -> Optional[Path]:
        """Download DC-DC datasheet"""
        filename = f"{mpn}_datasheet.pdf"
        output_path = self.output_dir / filename
        
        if output_path.exists():
            print(f"  [OK] Already exists: {filename}")
            return output_path
        
        try:
            print(f"  [DOWNLOADING] {mpn}...", end=" ", flush=True)
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            output_path.write_bytes(response.content)
            print(f"[OK] ({len(response.content) // 1024} KB)")
            return output_path
            
        except Exception as e:
            print(f"[WARN] Failed: {e}")
            return None
    
    def extract_dcdc_specs(self, pdf_path: Path, mpn: str, topology: str) -> Dict[str, Any]:
        """Extract DC-DC converter specifications"""
        print(f"  [PARSING] {mpn}...")
        
        pdf_bytes = pdf_path.read_bytes()
        pdf_result = self.pdf_parser.parse(pdf_bytes)
        
        if not pdf_result or "pages" not in pdf_result:
            print(f"  [WARN] Failed to parse PDF")
            return {}
        
        full_text = " ".join([page.get("text", "") for page in pdf_result.get("pages", [])])
        
        specs = {"topology": topology}
        
        # Input voltage
        vin_pattern = r'Input.*?Voltage.*?(\d+\.?\d*)\s*V.*?to.*?(\d+\.?\d*)\s*V'
        vin_match = re.search(vin_pattern, full_text, re.IGNORECASE)
        if vin_match:
            specs['input_voltage_min_v'] = float(vin_match.group(1))
            specs['input_voltage_max_v'] = float(vin_match.group(2))
        
        # Output voltage
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
            if iout_match.group(2).lower() == 'ma':
                current = current / 1000.0
            specs['output_current_max_a'] = current
        
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
        
        # Quiescent current
        iq_pattern = r'Quiescent.*?Current.*?(\d+\.?\d*)\s*(μA|uA|mA)'
        iq_match = re.search(iq_pattern, full_text, re.IGNORECASE)
        if iq_match:
            iq = float(iq_match.group(1))
            unit = iq_match.group(2).lower()
            if 'ma' in unit:
                iq = iq * 1000
            specs['quiescent_current_ua'] = iq
        
        return specs
    
    async def insert_dcdc(self, conn: asyncpg.Connection, mpn: str, manufacturer: str,
                          specs: Dict[str, Any]) -> uuid.UUID:
        """Insert DC-DC converter into database"""
        
        part_id = await conn.fetchval("""
            INSERT INTO parts (mpn, manufacturer, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (mpn) DO UPDATE
            SET status = EXCLUDED.status
            RETURNING id
        """, mpn, manufacturer, "active")
        
        await conn.execute("""
            INSERT INTO dcdc_specs (
                part_id, topology, input_voltage_min_v, input_voltage_max_v,
                output_voltage_min_v, output_voltage_max_v,
                output_current_max_a, efficiency_percent,
                switching_frequency_khz, quiescent_current_ua
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (part_id) DO UPDATE
            SET topology = EXCLUDED.topology
        """, 
            part_id, specs.get('topology'),
            specs.get('input_voltage_min_v'), specs.get('input_voltage_max_v'),
            specs.get('output_voltage_min_v'), specs.get('output_voltage_max_v'),
            specs.get('output_current_max_a'), specs.get('efficiency_percent'),
            specs.get('switching_frequency_khz'), specs.get('quiescent_current_ua')
        )
        
        print(f"  [OK] Inserted {mpn}")
        return part_id
    
    async def ingest_all(self):
        """Ingest all DC-DC converters"""
        print(f"\n{'='*60}")
        print(f"DC-DC Converter Ingestion Started")
        print(f"{'='*60}\n")
        
        conn = await asyncpg.connect(self.db_url)
        
        try:
            total = 0
            
            print("\n--- TI TPS62xxx Series ---")
            for dcdc in self.ti_dcdc:
                print(f"\n[{dcdc['mpn']}]")
                pdf_path = self.download_datasheet(dcdc["mpn"], dcdc["url"])
                if not pdf_path:
                    continue
                
                specs = self.extract_dcdc_specs(pdf_path, dcdc["mpn"], dcdc["topology"])
                if specs:
                    await self.insert_dcdc(conn, dcdc["mpn"], "Texas Instruments", specs)
                    total += 1
            
            print("\n--- Linear Tech LT3xxx Series ---")
            for dcdc in self.lt_dcdc:
                print(f"\n[{dcdc['mpn']}]")
                pdf_path = self.download_datasheet(dcdc["mpn"], dcdc["url"])
                if not pdf_path:
                    continue
                
                specs = self.extract_dcdc_specs(pdf_path, dcdc["mpn"], dcdc["topology"])
                if specs:
                    await self.insert_dcdc(conn, dcdc["mpn"], "Analog Devices", specs)
                    total += 1
            
            print(f"\n{'='*60}")
            print(f"✓ Ingested {total} DC-DC converters")
            print(f"{'='*60}\n")
            
        finally:
            await conn.close()


async def main():
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    ingester = DCDCIngester(db_url)
    await ingester.ingest_all()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
