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
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
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
                manufacturer TEXT,
                family TEXT,
                status TEXT,
                datasheet_url TEXT,
                package_family TEXT,
                package_name TEXT,
                pin_count INTEGER,
                theta_ja_c_w REAL,
                temp_min_c INTEGER DEFAULT -40,
                temp_max_c INTEGER DEFAULT 85,
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
                ram_kb INTEGER,
                sram_kb INTEGER,
                eeprom_kb INTEGER,
                can_count INTEGER DEFAULT 0,
                can_fd_count INTEGER DEFAULT 0,
                uart_count INTEGER DEFAULT 0,
                spi_count INTEGER DEFAULT 0,
                i2c_count INTEGER DEFAULT 0,
                usb_fs INTEGER DEFAULT 0,
                usb_hs INTEGER DEFAULT 0,
                usb_count INTEGER DEFAULT 0,
                ethernet INTEGER DEFAULT 0,
                adc_channels INTEGER DEFAULT 0,
                adc_count INTEGER DEFAULT 0,
                dac_channels INTEGER DEFAULT 0,
                dac_count INTEGER DEFAULT 0,
                timers_count INTEGER DEFAULT 0,
                timer_count INTEGER DEFAULT 0,
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
        
        # User selections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_selections (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                query_text TEXT,
                query_type TEXT,
                results_shown TEXT,
                result_count INTEGER,
                selected_part_id TEXT,
                selection_rank INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Audit trail table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                action TEXT,
                entity_type TEXT,
                entity_id TEXT,
                changes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Pin functions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcu_pin_functions (
                id TEXT PRIMARY KEY,
                part_id TEXT,
                pin_number TEXT,
                pin_name TEXT,
                af0_function TEXT, af1_function TEXT, af2_function TEXT, af3_function TEXT,
                af4_function TEXT, af5_function TEXT, af6_function TEXT, af7_function TEXT,
                af8_function TEXT, af9_function TEXT, af10_function TEXT, af11_function TEXT,
                af12_function TEXT, af13_function TEXT, af14_function TEXT, af15_function TEXT,
                has_adc INTEGER DEFAULT 0,
                has_dac INTEGER DEFAULT 0,
                is_power_pin INTEGER DEFAULT 0,
                is_boot_pin INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conflicts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conflicts (
                id TEXT PRIMARY KEY,
                part_id TEXT,
                conflict_type TEXT,
                description TEXT,
                severity TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Requirement specs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirement_specs (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                project_name TEXT,
                spec TEXT,
                source_text TEXT,
                mode TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Recommendation logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendation_logs (
                id TEXT PRIMARY KEY,
                spec_id TEXT,
                candidates TEXT,
                explanations TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Power modes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS power_modes (
                id TEXT PRIMARY KEY,
                part_id TEXT,
                mode_name TEXT,
                conditions TEXT,
                current_typ_ua REAL,
                current_max_ua REAL,
                voltage_v REAL,
                frequency_mhz REAL
            )
        """)

        # Other component spec tables
        cursor.execute("CREATE TABLE IF NOT EXISTS ldo_specs (id TEXT PRIMARY KEY, part_id TEXT, vin_min_v REAL, vin_max_v REAL, vout_fixed_v REAL, iout_max_ma REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS dcdc_specs (id TEXT PRIMARY KEY, part_id TEXT, vin_min_v REAL, vin_max_v REAL, vout_fixed_v REAL, iout_max_ma REAL)")
        cursor.execute("CREATE TABLE IF NOT EXISTS pmic_specs (id TEXT PRIMARY KEY, part_id TEXT, buck_count INTEGER, ldo_count INTEGER)")
        cursor.execute("CREATE TABLE IF NOT EXISTS can_specs (id TEXT PRIMARY KEY, part_id TEXT, data_rate_mbps REAL)")
        
        # Pin mux constraints table (required by PinMuxSolver.get_constraints())
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pin_mux_constraints (
                id TEXT PRIMARY KEY,
                part_id TEXT NOT NULL,
                constraint_type TEXT NOT NULL,
                pin_names TEXT NOT NULL,
                description TEXT,
                voltage_v REAL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS sensor_specs (id TEXT PRIMARY KEY, part_id TEXT, sensor_type TEXT, interface TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS passive_specs (id TEXT PRIMARY KEY, part_id TEXT, type TEXT, value_primary REAL, package_case TEXT)")
        
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
    
    def _preprocess_query(self, query: str) -> str:
        """Convert PostgreSQL syntax to SQLite"""
        # Replace ILIKE with LIKE (SQLite LIKE is case-insensitive by default for ASCII)
        query = query.replace("ILIKE", "LIKE")
        
        # Replace NOW() with CURRENT_TIMESTAMP
        query = query.replace("NOW()", "CURRENT_TIMESTAMP")
        
        # Replace $1, $2, etc with ?
        # Use a lookahead/lookbehind or word boundary to ensure we match the whole number
        import re
        query = re.sub(r'\$\d+', '?', query)
        
        return query

    def _preprocess_params(self, params):
        """Convert unsupported types like UUID to strings for SQLite"""
        import uuid
        import json
        processed = []
        for p in params:
            if isinstance(p, uuid.UUID):
                processed.append(str(p))
            elif isinstance(p, (dict, list)):
                processed.append(json.dumps(p))
            else:
                processed.append(p)
        return tuple(processed)

    async def execute(self, query: str, *params):
        """Execute query (async wrapper)"""
        query = self._preprocess_query(query)
        params = self._preprocess_params(params)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor.lastrowid
    
    async def fetchval(self, query: str, *params):
        """Fetch single value"""
        query = self._preprocess_query(query)
        params = self._preprocess_params(params)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return row[0] if row else None
    
    async def fetch(self, query: str, *params) -> List[Dict]:
        """Fetch all rows as dicts"""
        query = self._preprocess_query(query)
        params = self._preprocess_params(params)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def fetchrow(self, query: str, *params) -> Optional[Dict]:
        """Fetch single row as dict"""
        query = self._preprocess_query(query)
        params = self._preprocess_params(params)
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
        global _mock_db
        _mock_db = None


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
