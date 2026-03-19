import os
import asyncio
import asyncpg

async def check_db():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    print(f"Connecting to: {db_url}")
    try:
        conn = await asyncpg.connect(db_url)
        
        # Get all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print(f"{'Table Name':<30} | {'Row Count':<10}")
        print("-" * 45)
        
        for table in tables:
            name = table['table_name']
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {name}")
            print(f"{name:<30} | {count:<10}")
            
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_db())
