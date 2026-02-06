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
        if not self.database_url:
            raise ValueError(
                "Database URL must be provided either as argument or via DATABASE_URL environment variable"
            )
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self, min_size: int = 10, max_size: int = 20):
        """
        Create connection pool.
        
        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        logger.info("Creating database connection pool")
        
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
        )
        
        logger.info("Database connection pool created")
    
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


# Global database instance
db = Database()
