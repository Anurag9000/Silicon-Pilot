
import asyncio
import asyncpg
import os
import sys
import logging
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.stm32_datasheet_extractor import STM32DatasheetExtractor
from ingestion.downloader import DatasheetDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ingestion_full.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def run_full_ingestion(limit: int = 100):
    conn = await asyncpg.connect(DB_URL)
    downloader = DatasheetDownloader()
    
    try:
        # Get parts with datasheet URLs that haven't been updated recently?
        # For now, just get all valid STM32 parts
        # Prioritize F405 for demonstration if present
        rows = await conn.fetch("""
            SELECT id, mpn, datasheet_url 
            FROM parts 
            WHERE datasheet_url IS NOT NULL 
            AND manufacturer = 'STMicroelectronics'
            ORDER BY CASE WHEN mpn LIKE 'STM32F405%' THEN 0 ELSE 1 END, mpn
            LIMIT $1
        """, limit)
            
        logger.info(f"Found {len(rows)} parts to process.")
        
        success_count = 0
        
        for row in rows:
            part_id = row['id']
            mpn = row['mpn']
            url = row['datasheet_url']
            
            filename = f"{mpn}.pdf"
            
            logger.info(f"Processing {mpn}...")
            
            # 1. Download
            pdf_path = downloader.download(url, filename)
            
            if not pdf_path:
                logger.warning(f"  Could not obtain datasheet for {mpn}. Skipping.")
                continue
                
            # 2. Extract & Save
            try:
                extractor = STM32DatasheetExtractor(pdf_path)
                await extractor.save_to_db(conn, part_id)
                logger.info(f"  ✅ Extraction complete for {mpn}")
                success_count += 1
            except Exception as e:
                logger.error(f"  ❌ Extraction failed for {mpn}: {e}")
                
        logger.info(f"Full ingestion batch complete. Successfully processed {success_count}/{len(rows)} parts.")

    finally:
        await conn.close()

if __name__ == "__main__":
    # Allow limit override
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_full_ingestion(limit))
