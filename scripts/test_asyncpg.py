
import asyncio
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def test():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
        
        # Check parts
        count = await conn.fetchval("SELECT COUNT(*) FROM parts")
        print(f"Parts count: {count}")
        
        # Check mcu_specs
        print("Querying mcu_specs...")
        try:
            count = await conn.fetchval("SELECT COUNT(*) FROM mcu_specs")
            print(f"mcu_specs count: {count}")
        except Exception as e:
            print(f"mcu_specs Error: {e}")
            
        await conn.close()
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test())
