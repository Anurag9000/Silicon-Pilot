
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.pricing_fetcher import PricingFetcher

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def run_pricing_update():
    conn = await asyncpg.connect(DB_URL)
    try:
        fetcher = PricingFetcher()
        await fetcher.batch_update_prices(conn)
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_pricing_update())
