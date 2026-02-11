"""
STM32 Ingestion with Mock Database Support

Runs ingestion using SQLite if PostgreSQL not available.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable mock database if PostgreSQL not available
try:
    import psycopg2
    psycopg2.connect(host="localhost", port=5432, user="postgres", password="postgres", database="postgres", connect_timeout=1)
    print("✓ Using PostgreSQL")
    use_mock = False
except:
    print("⚠ PostgreSQL not available, using SQLite mock database")
    from core.mock_database import enable_mock_mode
    enable_mock_mode()
    use_mock = True

from ingestion.run_stm32_ingestion import STM32CompleteIngester


async def main():
    ingester = STM32CompleteIngester()
    
    try:
        await ingester.initialize()
        await ingester.ingest_all()
    finally:
        await ingester.close()


if __name__ == "__main__":
    asyncio.run(main())
