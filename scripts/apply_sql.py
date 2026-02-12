
import asyncio
import asyncpg
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_sql_file(file_path: str, db_url: str):
    """Apply a SQL file to the database"""
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False

    logger.info(f"Applying SQL file: {file_path}")
    
    try:
        conn = await asyncpg.connect(db_url)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
                
            await conn.execute(sql_content)
            logger.info("Successfully applied SQL.")
            return True
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Error applying SQL: {e}")
        return False

async def main():
    if len(sys.argv) < 2:
        print("Usage: python apply_sql.py <path_to_sql_file>")
        sys.exit(1)
        
    sql_file = sys.argv[1]
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    
    success = await apply_sql_file(sql_file, db_url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
