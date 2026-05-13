"""
LDO (Low Dropout Regulator) Ingester

Ingests LDO data from TI TPS7xxxx series and Analog Devices.

Features:
- Downloads datasheets
- Extracts LDO specifications
- Stores in ldo_specs table
"""

import asyncio
import asyncpg
import requests
import uuid
import re
from pathlib import Path
from typing import Dict, Any, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ingestion.pdf_parser import PDFParser


class LDOIngester:
    """Ingest LDO regulator data"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pdf_parser = PDFParser()
        self.output_dir = Path("data/ldo_datasheets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # TI TPS7xxxx series
        self.ti_ldo = [
            {"mpn": "TPS7A02", "url": "https://www.ti.com/lit/ds/symlink/tps7a02.pdf"},
            {"mpn": "TPS7A03", "url": "https://www.ti.com/lit/ds/symlink/tps7a03.pdf"},
            {"mpn": "TPS7A05", "url": "https://www.ti.com/lit/ds/symlink/tps7a05.pdf"},
            {"mpn": "TPS7A20", "url": "https://www.ti.com/lit/ds/symlink/tps7a20.pdf"},
            {"mpn": "TPS7A30", "url": "https://www.ti.com/lit/ds/symlink/tps7a30.pdf"},
            {"mpn": "TPS7A39", "url": "https://www.ti.com/lit/ds/symlink/tps7a39.pdf"},
            {"mpn": "TPS7A47", "url": "https://www.ti.com/lit/ds/symlink/tps7a47.pdf"},
            {"mpn": "TPS7A49", "url": "https://www.ti.com/lit/ds/symlink/tps7a49.pdf"},
            {"mpn": "TPS7A52", "url": "https://www.ti.com/lit/ds/symlink/tps7a52.pdf"},
            {"mpn": "TPS7A53", "url": "https://www.ti.com/lit/ds/symlink/tps7a53.pdf"},
            {"mpn": "TPS7A54", "url": "https://www.ti.com/lit/ds/symlink/tps7a54.pdf"},
            {"mpn": "TPS7A57", "url": "https://www.ti.com/lit/ds/symlink/tps7a57.pdf"},
            {"mpn": "TPS7A74", "url": "https://www.ti.com/lit/ds/symlink/tps7a74.pdf"},
            {"mpn": "TPS7A78", "url": "https://www.ti.com/lit/ds/symlink/tps7a78.pdf"},
            {"mpn": "TPS7A80", "url": "https://www.ti.com/lit/ds/symlink/tps7a80.pdf"},
            {"mpn": "TPS7A83", "url": "https://www.ti.com/lit/ds/symlink/tps7a83.pdf"},
            {"mpn": "TPS7A84", "url": "https://www.ti.com/lit/ds/symlink/tps7a84.pdf"},
            {"mpn": "TPS7A85", "url": "https://www.ti.com/lit/ds/symlink/tps7a85.pdf"},
            {"mpn": "TPS7A87", "url": "https://www.ti.com/lit/ds/symlink/tps7a87.pdf"},
            {"mpn": "TPS7A90", "url": "https://www.ti.com/lit/ds/symlink/tps7a90.pdf"},
        ]
        
        # Analog Devices LDOs
        self.adi_ldo = [
            {"mpn": "ADP150", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP150.pdf"},
            {"mpn": "ADP160", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP160.pdf"},
            {"mpn": "ADP170", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP170.pdf"},
            {"mpn": "ADP1706", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1706.pdf"},
            {"mpn": "ADP1707", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1707.pdf"},
            {"mpn": "ADP1708", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1708.pdf"},
            {"mpn": "ADP1710", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1710.pdf"},
            {"mpn": "ADP1712", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1712.pdf"},
            {"mpn": "ADP1713", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1713.pdf"},
            {"mpn": "ADP1714", "url": "https://www.analog.com/media/en/technical-documentation/data-sheets/ADP1714.pdf"},
        ]
    
    def download_datasheet(self, mpn: str, url: str) -> Optional[Path]:
        """Download LDO datasheet"""
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
    
    def extract_ldo_specs(self, pdf_path: Path, mpn: str) -> Dict[str, Any]:
        """Extract LDO specifications"""
        print(f"  [PARSING] {mpn}...")
        
        pdf_bytes = pdf_path.read_bytes()
        pdf_result = self.pdf_parser.parse(pdf_bytes)
        
        if not pdf_result or "pages" not in pdf_result:
            print(f"  [WARN] Failed to parse PDF")
            return {}
        
        full_text = " ".join([page.get("text", "") for page in pdf_result.get("pages", [])])
        
        specs = {}
        
        # Input voltage
        vin_pattern = r'Input.*?Voltage.*?(\d+\.?\d*)\s*V.*?to.*?(\d+\.?\d*)\s*V'
        vin_match = re.search(vin_pattern, full_text, re.IGNORECASE)
        if vin_match:
            specs['input_voltage_min_v'] = float(vin_match.group(1))
            specs['input_voltage_max_v'] = float(vin_match.group(2))
        
        # Output voltage
        vout_pattern = r'Output.*?Voltage.*?(\d+\.?\d*)\s*V'
        vout_match = re.search(vout_pattern, full_text, re.IGNORECASE)
        if vout_match:
            specs['output_voltage_v'] = float(vout_match.group(1))
        
        # Output current
        iout_pattern = r'Output.*?Current.*?(\d+\.?\d*)\s*(m?A)'
        iout_match = re.search(iout_pattern, full_text, re.IGNORECASE)
        if iout_match:
            current = float(iout_match.group(1))
            if iout_match.group(2).lower() == 'ma':
                current = current / 1000.0
            specs['output_current_max_a'] = current
        
        # Dropout voltage
        dropout_pattern = r'Dropout.*?Voltage.*?(\d+\.?\d*)\s*(m?V)'
        dropout_match = re.search(dropout_pattern, full_text, re.IGNORECASE)
        if dropout_match:
            dropout = float(dropout_match.group(1))
            if dropout_match.group(2).lower() == 'v':
                dropout = dropout * 1000
            specs['dropout_voltage_mv'] = dropout
        
        # Quiescent current
        iq_pattern = r'Quiescent.*?Current.*?(\d+\.?\d*)\s*(μA|uA|mA)'
        iq_match = re.search(iq_pattern, full_text, re.IGNORECASE)
        if iq_match:
            iq = float(iq_match.group(1))
            unit = iq_match.group(2).lower()
            if 'ma' in unit:
                iq = iq * 1000
            specs['quiescent_current_ua'] = iq
        
        # PSRR
        psrr_pattern = r'PSRR.*?(\d+)\s*dB'
        psrr_match = re.search(psrr_pattern, full_text, re.IGNORECASE)
        if psrr_match:
            specs['psrr_db'] = int(psrr_match.group(1))
        
        # Noise
        noise_pattern = r'Noise.*?(\d+\.?\d*)\s*(μV|uV)'
        noise_match = re.search(noise_pattern, full_text, re.IGNORECASE)
        if noise_match:
            specs['noise_uv_rms'] = float(noise_match.group(1))
        
        return specs
    
    async def insert_ldo(self, conn: asyncpg.Connection, mpn: str, manufacturer: str,
                         specs: Dict[str, Any]) -> uuid.UUID:
        """Insert LDO into database"""
        
        part_id = await conn.fetchval("""
            INSERT INTO parts (mpn, manufacturer, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (mpn) DO UPDATE
            SET status = EXCLUDED.status
            RETURNING id
        """, mpn, manufacturer, "active")
        
        await conn.execute("""
            INSERT INTO ldo_specs (
                part_id, input_voltage_min_v, input_voltage_max_v,
                output_voltage_v, output_current_max_a,
                dropout_voltage_mv, quiescent_current_ua,
                psrr_db, noise_uv_rms
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (part_id) DO UPDATE
            SET output_voltage_v = EXCLUDED.output_voltage_v
        """, 
            part_id,
            specs.get('input_voltage_min_v'), specs.get('input_voltage_max_v'),
            specs.get('output_voltage_v'), specs.get('output_current_max_a'),
            specs.get('dropout_voltage_mv'), specs.get('quiescent_current_ua'),
            specs.get('psrr_db'), specs.get('noise_uv_rms')
        )
        
        print(f"  [OK] Inserted {mpn}")
        return part_id
    
    async def ingest_all(self):
        """Ingest all LDOs"""
        print(f"\n{'='*60}")
        print(f"LDO Ingestion Started")
        print(f"{'='*60}\n")
        
        conn = await asyncpg.connect(self.db_url)
        
        try:
            total = 0
            
            print("\n--- TI TPS7Axxx Series ---")
            for ldo in self.ti_ldo:
                print(f"\n[{ldo['mpn']}]")
                pdf_path = self.download_datasheet(ldo["mpn"], ldo["url"])
                if not pdf_path:
                    continue
                
                specs = self.extract_ldo_specs(pdf_path, ldo["mpn"])
                if specs:
                    await self.insert_ldo(conn, ldo["mpn"], "Texas Instruments", specs)
                    total += 1
            
            print("\n--- Analog Devices ADP Series ---")
            for ldo in self.adi_ldo:
                print(f"\n[{ldo['mpn']}]")
                pdf_path = self.download_datasheet(ldo["mpn"], ldo["url"])
                if not pdf_path:
                    continue
                
                specs = self.extract_ldo_specs(pdf_path, ldo["mpn"])
                if specs:
                    await self.insert_ldo(conn, ldo["mpn"], "Analog Devices", specs)
                    total += 1
            
            print(f"\n{'='*60}")
            print(f"✓ Ingested {total} LDOs")
            print(f"{'='*60}\n")
            
        finally:
            await conn.close()


async def main():
    import os
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    ingester = LDOIngester(db_url)
    await ingester.ingest_all()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
