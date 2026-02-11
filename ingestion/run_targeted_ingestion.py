
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.stm32_datasheet_extractor import STM32DatasheetExtractor

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def run_ingestion(part_mpn: str = None, pdf_path: str = None):
    conn = await asyncpg.connect(DB_URL)
    try:
        # Get parts to process
        if part_mpn:
            rows = await conn.fetch("SELECT id, mpn, datasheet_url FROM parts WHERE mpn ILIKE $1", f"%{part_mpn}%")
        else:
            rows = await conn.fetch("SELECT id, mpn, datasheet_url FROM parts WHERE datasheet_url IS NOT NULL LIMIT 10")
            
        print(f"Found {len(rows)} parts to process.")
        
        for row in rows:
            part_id = row['id']
            mpn = row['mpn']
            url = row['datasheet_url']
            
            print(f"Processing {mpn}...")
            
            # Determine local path
            # Strategy: Logic to map URL to local file or download
            # For this test script, we use the provided PDF_PATH override if simple
            
            final_pdf_path = None
            
            if pdf_path and os.path.exists(pdf_path):
                # Force use of this PDF for testing
                final_pdf_path = pdf_path
            else:
                # Look in datasheets folder
                filename = url.split('/')[-1]
                local_path = Path(f"datasheets/{filename}")
                if local_path.exists():
                    final_pdf_path = str(local_path)
                elif Path("datasheets/stm32f405.pdf").exists(): # Fallback for demo
                     final_pdf_path = "datasheets/stm32f405.pdf"
            
            if not final_pdf_path:
                print(f"  No local datasheet found for {mpn}. Skipping.")
                continue
                
            print(f"  Using datasheet: {final_pdf_path}")
            
            # Run Extraction
            extractor = STM32DatasheetExtractor(final_pdf_path)
            await extractor.save_to_db(conn, part_id)
            print(f"  ✅ Extraction complete for {mpn}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    # Example usage: python ingestion/run_targeted_ingestion.py STM32F405 datasheets/mock_stm32.pdf
    mpn_arg = sys.argv[1] if len(sys.argv) > 1 else "STM32F405"
    pdf_arg = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(run_ingestion(mpn_arg, pdf_arg))
