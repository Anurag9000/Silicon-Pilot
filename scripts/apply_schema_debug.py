import asyncio
import asyncpg
import os

DB_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

async def apply_file(conn, filename):
    print(f"Applying {filename}...")
    try:
        with open(filename, "r") as f:
            sql = f.read()
        await conn.execute(sql)
        print(f"✓ {filename} executed.")
    except Exception as e:
        print(f"✗ Error applying {filename}: {e}")
        # Continue to see if other things work

async def list_tables(conn):
    print("\nListing current tables in 'public' schema:")
    rows = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    if not rows:
        print("  (No tables found)")
    for row in rows:
        print(f"  - {row['table_name']}")
    return [r['table_name'] for r in rows]

async def main():
    print(f"Connecting to {DB_URL}...")
    try:
        conn = await asyncpg.connect(DB_URL)
        print("Connected.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    try:
        # 1. Apply schema.sql
        await apply_file(conn, "database/schema.sql")
        
        # 2. Apply component_tables.sql
        await apply_file(conn, "database/component_tables.sql")
        
        # 3. Apply reference_design_schema.sql
        await apply_file(conn, "database/reference_design_schema.sql")
        
        # 4. Apply firmware_stack_schema.sql
        await apply_file(conn, "database/firmware_stack_schema.sql")

        # 5. Apply other schemas
        await apply_file(conn, "database/pin_mux_schema.sql")
        await apply_file(conn, "database/power_budget_schema.sql")
        await apply_file(conn, "database/ml_ranking_schema.sql")

        # 6. Verify tables
        tables = await list_tables(conn)
        
        required = ['parts', 'mcu_specs', 'reference_designs', 'firmware_stacks']
        missing = [t for t in required if t not in tables]
        
        if missing:
            print(f"\nCRITICAL: Missing tables: {missing}")
        else:
            print("\nSUCCESS: All core tables exist.")

    finally:
        await conn.close()
        
if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
