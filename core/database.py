"""
Database Connection Utility

Manages PostgreSQL connection pool and provides database access.
NO mock/SQLite fallback — production PostgreSQL only.
"""

import logging
import asyncpg
from typing import Optional
import os

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager — PostgreSQL only."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self, min_size: int = 5, max_size: int = 20):
        """
        Create connection pool to PostgreSQL.

        Args:
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Set it to your PostgreSQL connection string, e.g. "
                "postgresql://user:password@localhost:5432/siliconpilot"
            )

        logger.info(f"Connecting to PostgreSQL: {self.database_url.split('@')[-1]}")

        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
        )
        logger.info("✅ PostgreSQL connection pool created successfully")

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def switch_to_production(self, postgres_url: str):
        """Hot-swap the active database connection to a new PostgreSQL URL."""
        logger.info("INITIATING HOT-SWAP: Switching to new PostgreSQL URL...")

        new_pool = await asyncpg.create_pool(postgres_url)

        async with new_pool.acquire() as conn:
            await conn.execute("SELECT 1")

        old_pool = self.pool
        self.pool = new_pool
        self.database_url = postgres_url

        if old_pool:
            await old_pool.close()

        logger.info("HOT-SWAP COMPLETE: Backend is now rewired to new PostgreSQL database.")
        return True

    async def execute(self, query: str, *args):
        """Execute a query."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Fetch multiple rows."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Fetch single row."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Fetch single value."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def get_pool(self) -> asyncpg.Pool:
        """Get the connection pool (connecting if needed)."""
        if not self.pool:
            await self.connect()
        return self.pool


# Global database instance
db = Database()


async def get_pool() -> asyncpg.Pool:
    """Get the connection pool wrapper."""
    return await db.get_pool()
