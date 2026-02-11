"""
Mock Database Mode - SQLite Backend

Allows testing without PostgreSQL.
Automatically creates SQLite database with same schema.
"""

import sqlite3
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
import uuid


class MockDatabase:
    """SQLite-based mock database for testing"""
    
    def __init__(self, db_path: str = "data/hardwaregenius_mock.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
    
    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create tables matching PostgreSQL schema"""
        cursor = self.conn.cursor()
        
        # Parts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id TEXT PRIMARY KEY,
                mpn TEXT NOT NULL UNIQUE,
                manufacturer TEXT NOT NULL,
                family TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                package_family TEXT,
                package_name TEXT,
                pin_count INTEGER,
                temp_min_c INTEGER,
                temp_max_c INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # MCU specs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcu_specs (
                id TEXT PRIMARY KEY,
                part_id TEXT NOT NULL UNIQUE,
                core TEXT,
                max_mhz INTEGER,
                flash_kb INTEGER,
                sram_kb INTEGER,
                eeprom_kb INTEGER,
                can_count INTEGER DEFAULT 0,
                can_fd_count INTEGER DEFAULT 0,
                uart_count INTEGER DEFAULT 0,
                spi_count INTEGER DEFAULT 0,
                i2c_count INTEGER DEFAULT 0,
                usb_fs INTEGER DEFAULT 0,
                usb_hs INTEGER DEFAULT 0,
                ethernet INTEGER DEFAULT 0,
                adc_channels INTEGER DEFAULT 0,
                dac_channels INTEGER DEFAULT 0,
                timers_count INTEGER DEFAULT 0,
                pwm_channels INTEGER DEFAULT 0,
                has_fpu INTEGER DEFAULT 0,
                has_dsp INTEGER DEFAULT 0,
                has_crypto INTEGER DEFAULT 0,
                has_wireless INTEGER DEFAULT 0,
                vdd_min_v REAL,
                vdd_max_v REAL,
                active_ma REAL,
                standby_ua REAL,
                sleep_ua REAL,
                cost_usd REAL,
                extras TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE
            )
        """)
        
        # Documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_url TEXT UNIQUE,
                source_type TEXT,
                fetched_at TEXT,
                doc_hash TEXT,
                content_type TEXT,
                storage_key TEXT,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Evidence table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                part_id TEXT,
                field_path TEXT,
                extracted_value_raw TEXT,
                normalized_value TEXT,
                document_id TEXT,
                page INTEGER,
                bbox TEXT,
                snippet_storage_key TEXT,
                confidence REAL,
                parser_version TEXT,
                extracted_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (part_id) REFERENCES parts(id) ON DELETE CASCADE,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)
        
        self.conn.commit()
    
    async def execute(self, query: str, *params):
        """Execute query (async wrapper)"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.lastrowid
    
    async def fetchval(self, query: str, *params):
        """Fetch single value"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row else None
    
    async def fetch(self, query: str, *params) -> List[Dict]:
        """Fetch all rows as dicts"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *params) -> Optional[Dict]:
        """Fetch single row as dict"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()


# Global mock database instance
_mock_db = None


def get_mock_db() -> MockDatabase:
    """Get or create mock database"""
    global _mock_db
    if _mock_db is None:
        _mock_db = MockDatabase()
        _mock_db.connect()
    return _mock_db


# Mock pool for compatibility
class MockPool:
    """Mock asyncpg pool"""
    
    def __init__(self):
        self.db = get_mock_db()
    
    def acquire(self):
        """Return connection context manager"""
        return MockConnection(self.db)
    
    async def close(self):
        """Close pool"""
        self.db.close()


class MockConnection:
    """Mock asyncpg connection"""
    
    def __init__(self, db: MockDatabase):
        self.db = db
    
    async def __aenter__(self):
        return self.db
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


async def get_mock_pool() -> MockPool:
    """Get mock pool (replaces get_pool)"""
    return MockPool()


# Patch the database module
def enable_mock_mode():
    """Enable mock database mode"""
    import sys
    from pathlib import Path
    
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    # Patch core.database
    try:
        from core import database
        database.get_pool = get_mock_pool
        print("✓ Mock database mode enabled (SQLite)")
    except ImportError:
        print("⚠ Could not patch database module")


if __name__ == "__main__":
    # Test mock database
    enable_mock_mode()
    
    async def test():
        pool = await get_mock_pool()
        async with pool.acquire() as conn:
            # Test insert
            part_id = str(uuid.uuid4())
            await conn.execute(
                "INSERT INTO parts (id, mpn, manufacturer, status) VALUES (?, ?, ?, ?)",
                part_id, "TEST123", "TestMfg", "active"
            )
            
            # Test query
            count = await conn.fetchval("SELECT COUNT(*) FROM parts")
            print(f"✓ Parts in database: {count}")
            
            # Test fetch
            parts = await conn.fetch("SELECT * FROM parts")
            for part in parts:
                print(f"  - {part['mpn']} ({part['manufacturer']})")
        
        await pool.close()
    
    asyncio.run(test())
