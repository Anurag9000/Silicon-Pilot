import asyncio
import asyncpg
import os

DB_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

async def main():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
        
        print("Attempting naive insert into parts...")
        try:
            val = await conn.fetchval("""
                INSERT INTO parts (mpn, manufacturer, datasheet_url) 
                VALUES ('TEST-PART-001', 'TestManu', 'http://example.com')
                RETURNING id;
            """)
            print(f"Insert successful! ID: {val}")
        except Exception as e:
            print(f"Insert failed: {e}")
            
    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
