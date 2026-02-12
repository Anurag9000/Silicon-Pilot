
import asyncio
import asyncpg
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Verification")

async def verify():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    conn = await asyncpg.connect(db_url)
    
    tables = ["pmic_specs", "can_specs", "sensor_specs", "passive_specs"]
    
    try:
        print("\n=== Phase 3 Verification ===")
        for table in tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"Table '{table}': {count} rows")
            
        # Check parts description
        desc_count = await conn.fetchval("SELECT COUNT(*) FROM parts WHERE description IS NOT NULL")
        print(f"Parts with description: {desc_count}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())
