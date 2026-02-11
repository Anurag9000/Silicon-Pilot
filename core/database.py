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
            await self.pool.close()
            logger.info("Database connection pool closed")
    
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
