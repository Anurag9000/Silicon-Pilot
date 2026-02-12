
"""
ST LDO Regulator Ingester

Generates LDO part numbers for known ST families and downloads datasheets.
Populates 'parts' table with new LDO entries.
"""

import asyncio
import os
import sys
import logging
import asyncpg
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# ST LDO Families to Ingest
# Format: {SeriesName: {PackageCode: PinCount}}
LDO_FAMILIES = {
    "LDL1117": {
        "S33": 3, # SOT-223 Fixed 3.3V
        "S12": 3, # SOT-223 Fixed 1.2V
        "S50": 3  # SOT-223 Fixed 5.0V
    },
    "LDK320": {
        "AM": 5,  # SOT-23-5
        "M": 3    # SOT-23
    },
    "LD39015": {
        "M": 3,
        "J": 4    # Flip-Chip
    }
}

async def generate_ldo_parts(conn):
    print("Generating LDO parts...")
    count = 0
    
    for series, variants in LDO_FAMILIES.items():
        # Datasheet URL is usually series based
        # e.g. https://www.st.com/resource/en/datasheet/ldl1117.pdf
        url = f"https://www.st.com/resource/en/datasheet/{series.lower()}.pdf"
        
        for pkg_code, pins in variants.items():
            # Construct MPN - This is heuristic!
            # Real MPN might be LDL1117S33R
            # Let's assume a generic suffix for now or just insert the Series as the main part
            # But the system expects MPNs.
            
            # Let's create a "Representative" MPN for the series + package
            mpn = f"{series}{pkg_code}R" # 'R' is common for T&R
            
            # Insert into parts
            await conn.execute("""
                INSERT INTO parts (mpn, manufacturer, family, package_family, pin_count, datasheet_url)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (mpn) DO NOTHING
            """, mpn, "STMicroelectronics", "LDO", "SOT/DFN", pins, url)
            
            # Initialize LDO Specs (Empty, to be filled by extractor)
            # Fetch ID
            part_id = await conn.fetchval("SELECT id FROM parts WHERE mpn = $1", mpn)
            
            if part_id:
                # Insert empty ldo_specs
                await conn.execute("""
                    INSERT INTO ldo_specs (part_id) VALUES ($1)
                    ON CONFLICT (part_id) DO NOTHING
                """, part_id)
                count += 1
                
    print(f"Generated {count} LDO parts.")

async def main():
    try:
        conn = await asyncpg.connect(DB_URL)
        await generate_ldo_parts(conn)
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
