
"""
Run Errata Processing

Iterates over 'documents' table, finds Errata Sheets, and runs the Extractor
to populate 'errata_items'.
"""

import asyncio
import os
import sys
import logging
import asyncpg
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.stm32_errata_extractor import STM32ErrataExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def process_errata():
    try:
        conn = await asyncpg.connect(DB_URL)
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return

    # Fetch all errata sheets
    rows = await conn.fetch("""
        SELECT id, document_number, local_path 
        FROM documents 
        WHERE type = 'errata_sheet' AND local_path IS NOT NULL
    """)
    
    logger.info(f"Found {len(rows)} errata sheets to process.")
    
    for row in rows:
        doc_id = row['id']
        doc_num = row['document_number']
        path = row['local_path']
        
        if not os.path.exists(path):
            logger.warning(f"File not found: {path} (Doc: {doc_num})")
            continue
            
        logger.info(f"Processing {doc_num} from {path}...")
        
        try:
            extractor = STM32ErrataExtractor(path)
            await extractor.save_to_db(conn, doc_id)
            logger.info(f"✓ Saved errata items for {doc_num}")
        except Exception as e:
            logger.error(f"Failed to process {doc_num}: {e}")
            
    await conn.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(process_errata())
