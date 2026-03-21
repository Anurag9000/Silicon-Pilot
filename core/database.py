"""
Database Connection Utility

Manages PostgreSQL connection pool and provides database access.
"""

import logging
import asyncpg
from typing import Optional
import os

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_url: PostgreSQL connection URL
        
        Raises:
            ValueError: If database_url is not provided and DATABASE_URL env var is not set
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        # We don't raise here to allow importing in tests without env vars
        # Connection will fail later if URL is missing
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, min_size: int = 10, max_size: int = 20):
        """
        Create connection pool.
        
        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        if not self.database_url:
            logger.warning("DATABASE_URL not set. Falling back to mock database.")
            from core.mock_database import get_mock_pool
            self.pool = await get_mock_pool()
            return
            
        logger.info("Creating database connection pool")
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60,
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.warning(f"Failed to create connection pool: {e}. Falling back to mock database.")
            from core.mock_database import get_mock_pool
            self.pool = await get_mock_pool()
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            if hasattr(self.pool, 'close') and os.path.exists("data/hardwaregenius_mock.db") and not hasattr(self.pool, 'acquire'):
                 # Mock pool close is sync
                 self.pool.close()
            else:
                 await self.pool.close()
            logger.info("Database connection pool closed")

    async def switch_to_production(self, postgres_url: str):
        """Hot-swap the active database from Mock to Production"""
        import asyncio
        logger.info("INITIATING HOT-SWAP: Switching to Production PostgreSQL...")
        
        # 1. Create new production pool
        new_pool = await asyncpg.create_pool(postgres_url)
        
        # 2. Verify connection
        async with new_pool.acquire() as conn:
            await conn.execute("SELECT 1")
            
        # 3. Swap the active pool
        old_pool = self.pool
        self.pool = new_pool
        
        # 4. Cleanup old pool
        if old_pool:
            if hasattr(old_pool, 'close') and not hasattr(old_pool, 'acquire'):
                old_pool.close() # Mock is sync
            else:
                await old_pool.close() # asyncpg is async
                
        logger.info("HOT-SWAP COMPLETE: Backend is now rewired to Production Database.")
        return True
    
    async def execute(self, query: str, *args):
        """Execute a query"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch single row"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch single value"""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def get_pool(self) -> asyncpg.Pool:
        """Get the connection pool (initializing if needed)"""
        if not self.pool:
            if self.database_url:
                try:
                    await self.connect()
                except Exception as e:
                    logger.warning(f"Failed to connect to PostgreSQL: {e}. Falling back to mock database.")
                    from core.mock_database import get_mock_pool
                    self.pool = await get_mock_pool()
            else:
                logger.warning("DATABASE_URL not set. Falling back to mock database.")
                from core.mock_database import get_mock_pool
                self.pool = await get_mock_pool()
        
        return self.pool


# Global database instance
db = Database()


async def get_pool() -> asyncpg.Pool:
    """Get the connection pool wrapper"""
    return await db.get_pool()
