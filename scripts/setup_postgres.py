import asyncio
import os
import sys
from pathlib import Path
import asyncpg

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def setup_database():
    """Initialize PostgreSQL database with full schema"""
    
    # Force the working URL if env var is weird, but try env first
    # Using the one that WORKED in debug_connection.py
    default_url = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"
    db_url = os.getenv("DATABASE_URL", default_url)

    print(f"Connecting to {db_url}...")
    
    try:
        # Read SQL files
        base_dir = Path(__file__).parent.parent / "database"
        schema_sql = (base_dir / "schema.sql").read_text(encoding="utf-8")
        components_sql = (base_dir / "component_tables.sql").read_text(encoding="utf-8")
        
        full_schema = schema_sql + "\n\n" + components_sql
        
        # Connect and execute
        conn = await asyncpg.connect(db_url)
        try:
            print("Executing schema scripts...")
            await conn.execute(full_schema)
            print("✓ Schema initialized successfully!")
            
            # Verify tables
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            print(f"✓ Found {len(tables)} tables: {', '.join([t['table_name'] for t in tables])}")
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"❌ Database setup failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(setup_database())
