"""
Database Integration for Subsystem Solvers

Connects multi-subsystem solvers to the existing PostgreSQL database
instead of using curated lists. Enables real component recommendations
with evidence linking.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import asyncpg
from core.database import get_pool
from core.models import RequirementSpec


# ============================================================================
# Database-Connected Power Solver
# ============================================================================

class PowerSolverDB:
    """Power component solver connected to database"""
    
    async def solve(self, req: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find power components from database"""
        pool = await get_pool()
        
        if not pool:
            raise ValueError("Database connection not available")
        
        # Build query based on requirements
        query = """
            SELECT 
                p.mpn,
                p.manufacturer,
                ps.input_voltage_min,
                ps.input_voltage_max,
                ps.output_voltage,
                ps.output_current_ma,
                ps.efficiency_percent,
                ps.package,
                ps.price_usd,
                e.source_url,
                e.snippet_ref
            FROM parts p
            JOIN power_specs ps ON p.id = ps.part_id
            LEFT JOIN evidence e ON p.id = e.part_id
            WHERE ps.component_type = $1
                AND ps.input_voltage_min <= $2
                AND ps.input_voltage_max >= $3
                AND ps.output_voltage BETWEEN $4 AND $5
                AND ps.output_current_ma >= $6
            ORDER BY ps.price_usd ASC
            LIMIT 10
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                query,
                req.get("component_type", "buck"),
                req.get("input_voltage_max", 48),
                req.get("input_voltage_min", 5),
                req.get("output_voltage", 3.3) - 0.2,
                req.get("output_voltage", 3.3) + 0.2,
                req.get("output_current_ma", 500)
            )
        
        results = []
        for row in rows:
            results.append({
                "mpn": row["mpn"],
                "manufacturer": row["manufacturer"],
                "input_voltage_range": [row["input_voltage_min"], row["input_voltage_max"]],
                "output_voltage": row["output_voltage"],
                "output_current_ma": row["output_current_ma"],
                "efficiency_percent": row["efficiency_percent"],
                "package": row["package"],
                "price_usd": row["price_usd"],
                "evidence": {
                    "source_url": row["source_url"],
                    "snippet": row["snippet_ref"]
                }
            })
        
        return results


# ============================================================================
# Database-Connected Transceiver Solver
# ============================================================================

class TransceiverSolverDB:
    """Transceiver component solver connected to database"""
    
    async def solve(self, req: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find transceiver components from database"""
        pool = await get_pool()
        
        if not pool:
            raise ValueError("Database connection not available")
        
        query = """
            SELECT 
                p.mpn,
                p.manufacturer,
                ts.protocol,
                ts.interface,
                ts.voltage,
                ts.data_rate_kbps,
                ts.package,
                ts.price_usd,
                e.source_url
            FROM parts p
            JOIN transceiver_specs ts ON p.id = ts.part_id
            LEFT JOIN evidence e ON p.id = e.part_id
            WHERE ts.protocol = $1
                AND ts.voltage BETWEEN $2 AND $3
            ORDER BY ts.price_usd ASC
            LIMIT 10
        """
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                query,
                req.get("protocol", "can"),
                req.get("voltage", 3.3) - 0.3,
                req.get("voltage", 3.3) + 0.3
            )
        
        results = []
        for row in rows:
            results.append({
                "mpn": row["mpn"],
                "manufacturer": row["manufacturer"],
                "protocol": row["protocol"],
                "interface": row["interface"],
                "voltage": row["voltage"],
                "data_rate_kbps": row["data_rate_kbps"],
                "package": row["package"],
                "price_usd": row["price_usd"],
                "evidence": {
                    "source_url": row["source_url"]
                }
            })
        
        return results


# ============================================================================
# Database Schema for Additional Component Types
# ============================================================================

CREATE_POWER_SPECS_TABLE = """
CREATE TABLE IF NOT EXISTS power_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    component_type VARCHAR(50) NOT NULL,  -- buck, boost, ldo, pmic, charger
    input_voltage_min FLOAT,
    input_voltage_max FLOAT,
    output_voltage FLOAT,
    output_current_ma INTEGER,
    efficiency_percent FLOAT,
    quiescent_current_ua INTEGER,
    package VARCHAR(50),
    price_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(part_id)
);

CREATE INDEX idx_power_specs_type ON power_specs(component_type);
CREATE INDEX idx_power_specs_voltage ON power_specs(input_voltage_min, input_voltage_max, output_voltage);
CREATE INDEX idx_power_specs_current ON power_specs(output_current_ma);
"""

CREATE_TRANSCEIVER_SPECS_TABLE = """
CREATE TABLE IF NOT EXISTS transceiver_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    protocol VARCHAR(50) NOT NULL,  -- can, rs485, lora, ble, etc.
    interface VARCHAR(50),  -- spi, uart, i2c
    voltage FLOAT,
    data_rate_kbps INTEGER,
    package VARCHAR(50),
    price_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(part_id)
);

CREATE INDEX idx_transceiver_specs_protocol ON transceiver_specs(protocol);
CREATE INDEX idx_transceiver_specs_voltage ON transceiver_specs(voltage);
"""

CREATE_MEMORY_SPECS_TABLE = """
CREATE TABLE IF NOT EXISTS memory_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,  -- flash, eeprom, sram, fram
    capacity_kb INTEGER NOT NULL,
    interface VARCHAR(50) NOT NULL,  -- spi, i2c, parallel
    voltage FLOAT,
    speed_mhz INTEGER,
    power_ua INTEGER,
    package VARCHAR(50),
    price_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(part_id)
);

CREATE INDEX idx_memory_specs_type ON memory_specs(memory_type);
CREATE INDEX idx_memory_specs_capacity ON memory_specs(capacity_kb);
CREATE INDEX idx_memory_specs_interface ON memory_specs(interface);
"""

CREATE_DISPLAY_SPECS_TABLE = """
CREATE TABLE IF NOT EXISTS display_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
    display_type VARCHAR(50) NOT NULL,  -- lcd, oled, epaper
    resolution VARCHAR(20) NOT NULL,  -- "320x240"
    size_inches FLOAT,
    interface VARCHAR(50) NOT NULL,  -- spi, i2c, parallel, mipi_dsi
    color BOOLEAN DEFAULT false,
    touch BOOLEAN DEFAULT false,
    package VARCHAR(50),
    price_usd FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(part_id)
);

CREATE INDEX idx_display_specs_type ON display_specs(display_type);
CREATE INDEX idx_display_specs_resolution ON display_specs(resolution);
CREATE INDEX idx_display_specs_interface ON display_specs(interface);
"""


# ============================================================================
# Migration Script
# ============================================================================

async def migrate_subsystem_tables():
    """Create tables for subsystem components"""
    pool = await get_pool()
    
    if not pool:
        raise ValueError("Database connection not available")
    
    async with pool.acquire() as conn:
        # Create power specs table
        await conn.execute(CREATE_POWER_SPECS_TABLE)
        print("✓ Created power_specs table")
        
        # Create transceiver specs table
        await conn.execute(CREATE_TRANSCEIVER_SPECS_TABLE)
        print("✓ Created transceiver_specs table")
        
        # Create memory specs table
        await conn.execute(CREATE_MEMORY_SPECS_TABLE)
        print("✓ Created memory_specs table")
        
        # Create display specs table
        await conn.execute(CREATE_DISPLAY_SPECS_TABLE)
        print("✓ Created display_specs table")
    
    print("\n✅ All subsystem tables created successfully")


# ============================================================================
# Sample Data Ingestion
# ============================================================================

async def ingest_sample_power_components():
    """Ingest sample power components"""
    pool = await get_pool()
    
    sample_components = [
        {
            "mpn": "TPS62160",
            "manufacturer": "Texas Instruments",
            "component_type": "buck",
            "input_voltage_min": 3.0,
            "input_voltage_max": 17.0,
            "output_voltage": 3.3,
            "output_current_ma": 1000,
            "efficiency_percent": 95.0,
            "quiescent_current_ua": 17,
            "package": "SOT-23-6",
            "price_usd": 1.20
        },
        {
            "mpn": "MCP1700",
            "manufacturer": "Microchip",
            "component_type": "ldo",
            "input_voltage_min": 2.3,
            "input_voltage_max": 6.0,
            "output_voltage": 3.3,
            "output_current_ma": 250,
            "efficiency_percent": 85.0,
            "quiescent_current_ua": 1.6,
            "package": "SOT-23-3",
            "price_usd": 0.30
        },
    ]
    
    async with pool.acquire() as conn:
        for comp in sample_components:
            # Insert into parts table first
            part_id = await conn.fetchval(
                """
                INSERT INTO parts (mpn, manufacturer, family, status)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (mpn) DO UPDATE SET manufacturer = $2
                RETURNING id
                """,
                comp["mpn"],
                comp["manufacturer"],
                "Power Management",
                "active"
            )
            
            # Insert into power_specs
            await conn.execute(
                """
                INSERT INTO power_specs (
                    part_id, component_type, input_voltage_min, input_voltage_max,
                    output_voltage, output_current_ma, efficiency_percent,
                    quiescent_current_ua, package, price_usd
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (part_id) DO UPDATE SET
                    component_type = $2,
                    input_voltage_min = $3,
                    input_voltage_max = $4,
                    output_voltage = $5,
                    output_current_ma = $6,
                    efficiency_percent = $7,
                    quiescent_current_ua = $8,
                    package = $9,
                    price_usd = $10
                """,
                part_id,
                comp["component_type"],
                comp["input_voltage_min"],
                comp["input_voltage_max"],
                comp["output_voltage"],
                comp["output_current_ma"],
                comp["efficiency_percent"],
                comp["quiescent_current_ua"],
                comp["package"],
                comp["price_usd"]
            )
    
    print(f"✓ Ingested {len(sample_components)} power components")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("Creating subsystem tables...")
        await migrate_subsystem_tables()
        
        print("\nIngesting sample data...")
        await ingest_sample_power_components()
        
        print("\nTesting power solver...")
        solver = PowerSolverDB()
        results = await solver.solve({
            "component_type": "buck",
            "input_voltage_min": 5,
            "input_voltage_max": 12,
            "output_voltage": 3.3,
            "output_current_ma": 500
        })
        print(f"Found {len(results)} power components")
        for r in results:
            print(f"  {r['manufacturer']} {r['mpn']}: ${r['price_usd']}")
    
    asyncio.run(main())
