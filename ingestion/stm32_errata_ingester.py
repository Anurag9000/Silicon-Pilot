
"""
STM32 Errata & Reference Manual Ingester

Maps STM32 Series to their specific documentation IDs (Errata Sheets, Reference Manuals)
and downloads them to the local `datasheets/` directory.

Mapping Source:
Hardcoded for key families (Proof of Concept). In production, this would be scraped.
"""

import asyncio
import os
import sys
import logging
import asyncpg
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.downloader import DatasheetDownloader

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")

# Known Documentation Mapping
# Format: Series -> List of {type, id, title}
DOC_MAP = {
    # STM32F4 Series
    "STM32F405": [
        {"type": "errata_sheet", "id": "es0182", "title": "STM32F405/415/407/417 xx Errata sheet"},
        {"type": "reference_manual", "id": "rm0090", "title": "STM32F405/415, STM32F407/417, STM32F427/437 and STM32F429/439 advanced Arm-based 32-bit MCUs"},
    ],
    "STM32F407": [
        {"type": "errata_sheet", "id": "es0182", "title": "STM32F405/415/407/417 xx Errata sheet"},
        {"type": "reference_manual", "id": "rm0090", "title": "STM32F405/415, STM32F407/417, STM32F427/437 and STM32F429/439 advanced Arm-based 32-bit MCUs"},
    ],
    # STM32F1 Series
    "STM32F103": [
         {"type": "errata_sheet", "id": "es0016", "title": "STM32F101x8/B, STM32F102x8/B and STM32F103x8/B medium-density device limitations"},
         {"type": "reference_manual", "id": "rm0008", "title": "STM32F101xx, STM32F102xx, STM32F103xx, STM32F105xx and STM32F107xx advanced Arm-based 32-bit MCUs"},
    ],
    # STM32G0 Series
    "STM32G070": [
        {"type": "errata_sheet", "id": "es0418", "title": "STM32G070xB/x6 device limitations"},
        {"type": "reference_manual", "id": "rm0444", "title": "STM32G0x0 advanced Arm-based 32-bit MCUs"},
    ]
}

class ErrataIngester:
    def __init__(self, db_pool):
        self.db = db_pool
        self.downloader = DatasheetDownloader(download_dir="datasheets/docs")
        
    async def process_series(self, series: str, docs: list):
        """Process all docs for a specific series"""
        # Find parts belonging to this series
        # We assume 'parts' table has 'mpn' starting with series
        logger.info(f"Processing docs for Series: {series}")
        
        # Get IDs of parts in this series
        rows = await self.db.fetch("SELECT id, mpn FROM parts WHERE mpn LIKE $1 || '%'", series)
        if not rows:
            logger.warning(f"No parts found for series {series}")
            return

        part_ids = [r['id'] for r in rows]
        logger.info(f"Applying docs to {len(part_ids)} parts (e.g., {rows[0]['mpn']})")

        for doc in docs:
            doc_type = doc['type']
            doc_id = doc['id']
            title = doc['title']
            url = f"https://www.st.com/resource/en/{doc_type}/{doc_id}.pdf"
            
            # Download
            logger.info(f"Fetching {doc_id} ({doc_type})...")
            filename = f"{doc_id}.pdf"
            # DatasheetDownloader.download is synchronous
            path = self.downloader.download(url, filename)
            
            if not path:
                logger.error(f"Failed to download {doc_id}")
                continue
                
            # Insert into 'documents' table for EACH part in the series
            # (In a real optimized DB, we'd link to a 'family' table, but here we link to parts)
            
            # Optimization: Check if document exists first to avoid re-inserting for every part if already linked?
            # Actually, our schema links document -> part_id. So we have one row per part per document.
            # This is 1:N. Ideally we should have M:N (parts <-> documents).
            # But documents table has `part_id`.
            # If `is_generic` is True, we can just insert ONCE with null part_id?
            # The schema says: `is_generic BOOLEAN DEFAULT FALSE`.
            # Let's use `is_generic=True` for these Series-level docs to save space.
            
            # Check if doc exists generically
            existing = await self.db.fetchval(
                "SELECT id FROM documents WHERE document_number = $1 AND is_generic = TRUE", 
                doc_id
            )
            
            if existing:
                logger.info(f"Document {doc_id} already exists (Generic). Skipping re-insert.")
                continue
                
            # Insert Generic Document
            # We link it to the FIRST part_id just as a reference, or NULL if allowed.
            # Schema: part_id UUID REFERENCES parts(id). It is nullable?
            # Schema: `part_id UUID REFERENCES...` default is NULLABLE unless NOT NULL specified.
            # Checking errata_schema.sql: `part_id UUID REFERENCES ...` (Null allowed).
            
            logger.info(f"Registering generic document {doc_id} for series {series}")
            await self.db.execute("""
                INSERT INTO documents (
                    type, is_generic, document_number, title, url, local_path, part_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, doc_type, True, doc_id, title, url, str(path), part_ids[0])

async def main():
    try:
        pool = await asyncpg.create_pool(DB_URL)
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return

    ingester = ErrataIngester(pool)
    
    # Process known mappings
    for series, docs in DOC_MAP.items():
        await ingester.process_series(series, docs)
        
    await pool.close()
    logger.info("Errata Ingestion Complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
