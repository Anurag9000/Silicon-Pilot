
import sys
from pathlib import Path
# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from ingestion.pricing_fetcher import PricingFetcher

import asyncio
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def test():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
        
        # Test Fetcher
        print("Testing PricingFetcher.batch_update_prices...")
        fetcher = PricingFetcher()
        await fetcher.batch_update_prices(conn)
        
        await conn.close()
    except Exception as e:
        print(f"Connection Failed: {e}")
        
        # Check mcu_specs
        print("Querying mcu_specs...")
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM mcu_specs")
            print(f"mcu_specs count: {count}")
        except Exception as e:
            print(f"mcu_specs Error: {e}")
            
        # Check part_pricing
        print("Querying part_pricing...")
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM part_pricing")
            print(f"part_pricing count: {count}")
            
            print("Testing LEFT JOIN query...")
            rows = await conn.fetch("""
                SELECT p.id, p.mpn, p.family
                FROM parts p
                LEFT JOIN part_pricing pp ON p.id = pp.part_id
                WHERE pp.id IS NULL
            """)
            print(f"Join Query Rows: {len(rows)}")
            
        except Exception as e:
            print(f"part_pricing Error: {e}")
            
        await conn.close()
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
