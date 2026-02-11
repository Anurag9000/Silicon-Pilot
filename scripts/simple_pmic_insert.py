
import asyncio
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

async def test_insert():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
        
        # Check search path
        path = await conn.fetchval("SHOW search_path")
        print(f"Search path: {path}")
        
        # Check table visibility
        exists = await conn.fetchval("SELECT to_regclass('public.pmic_specs')")
        print(f"Table 'public.pmic_specs' exists: {exists}")
        
        exists_noprefix = await conn.fetchval("SELECT to_regclass('pmic_specs')")
        print(f"Table 'pmic_specs' exists: {exists_noprefix}")

        # Try insert
        print("Attempting INSERT...")
        try:
            # First get a part_id (or make one)
            # We need a part first.
            part_id = await conn.fetchval("""
                INSERT INTO parts (mpn, manufacturer, status) 
                VALUES ('DEBUG-PMIC-001', 'DebugManu', 'active') 
                ON CONFLICT (mpn) DO UPDATE SET status='active' RETURNING id
            """)
            print(f"Part ID: {part_id}")
            
            await conn.execute("""
                INSERT INTO pmic_specs (part_id, input_voltage_min_v)
                VALUES ($1, 3.3)
                ON CONFLICT (part_id) DO NOTHING
            """, part_id)
            print("INSERT successful.")
        except Exception as e:
            print(f"INSERT failed: {e}")
            
        await conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_insert())
