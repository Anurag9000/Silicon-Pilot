import asyncio
import asyncpg
import os

DB_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

async def main():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
        
        # Check specific tables
        tables = ['parts', 'mcu_specs', 'reference_designs', 'firmware_stacks', 
                  'pmic_specs', 'dcdc_specs', 'ldo_specs']
        print("\nChecking table existence:")
        
        for table in tables:
            exists = await conn.fetchval(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = '{table}'
                );
            """)
            print(f"  - {table}: {'FOUND' if exists else 'MISSING'}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
