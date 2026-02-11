import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from core.database import get_pool

async def check_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            # Check parts count
            count = await conn.fetchval("SELECT COUNT(*) FROM parts")
            print(f"Total Parts: {count}")
            
            # Check families
            families = await conn.fetch("SELECT family, COUNT(*) as c FROM parts GROUP BY family")
            print("\nBreakdown by Family:")
            for r in families:
                print(f"  {r['family']}: {r['c']}")
                
            # Check specs
            specs = await conn.fetchval("SELECT COUNT(*) FROM mcu_specs")
            print(f"\nTotal MCU Specs: {specs}")
            
        except Exception as e:
            print(f"Error querying DB: {e}")
        finally:
            await pool.close()

if __name__ == "__main__":
    asyncio.run(check_stats())
