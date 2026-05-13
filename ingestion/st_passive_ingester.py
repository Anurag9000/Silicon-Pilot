
"""
Ingester for Passive Components (Resistors, Capacitors)
"""

import asyncio
import logging
import asyncpg
import os
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Seed Data (Generic parts for reference designs)
PASSIVE_PARTS = [
    {
        "mpn": "GEN-RES-10K-0402-1%",
        "manufacturer": "Generic",
        "family": "Resistor",
        "description": "Resistor 10k Ohm 1% 1/16W 0402",
        "datasheet": "",
        "specs": {
            "type": "Resistor",
            "value_primary": 10000.0,
            "tolerance_percent": 1.0,
            "power_rating_w": 0.0625,
            "package_case": "0402"
        }
    },
    {
        "mpn": "GEN-CAP-100NF-0402-16V",
        "manufacturer": "Generic",
        "family": "Capacitor",
        "description": "Capacitor 100nF 16V X7R 0402",
        "datasheet": "",
        "specs": {
            "type": "Capacitor",
            "value_primary": 100e-9,
            "tolerance_percent": 10.0,
            "voltage_rating_v": 16.0,
            "package_case": "0402",
            "dielectric_type": "X7R"
        }
    },
    {
        "mpn": "GEN-CAP-10UF-0603-10V",
        "manufacturer": "Generic",
        "family": "Capacitor",
        "description": "Capacitor 10uF 10V X5R 0603",
        "datasheet": "",
        "specs": {
            "type": "Capacitor",
            "value_primary": 10e-6,
            "tolerance_percent": 20.0,
            "voltage_rating_v": 10.0,
            "package_case": "0603",
            "dielectric_type": "X5R"
        }
    }
]

class PassiveIngester:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def ingest_part(self, data: dict):
        """Ingest a passive part"""
        mpn = data['mpn']
        logger.info(f"Ingesting passive: {mpn}")
        
        async with self.db_pool.acquire() as conn:
            # 1. Upsert Part
            part_id = await conn.fetchval("SELECT id FROM parts WHERE mpn = $1", mpn)
            
            if not part_id:
                part_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO parts (id, mpn, manufacturer, family, description, datasheet_url, status)
                    VALUES ($1, $2, $3, $4, $5, $6, 'active')
                """, part_id, mpn, data['manufacturer'], data['family'], data['description'], data['datasheet'])
                logger.info(f"Created new part: {mpn}")
            else:
                logger.info(f"Updating existing part: {mpn}")
                await conn.execute("""
                    UPDATE parts SET description = $2, datasheet_url = $3
                    WHERE id = $1
                """, part_id, data['description'], data['datasheet'])
            
            # 2. Upsert Specs
            specs = data['specs']
            await conn.execute("""
                INSERT INTO passive_specs (
                    part_id, type, value_primary, tolerance_percent, 
                    power_rating_w, voltage_rating_v, package_case, dielectric_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (part_id) DO UPDATE SET
                    type = EXCLUDED.type,
                    value_primary = EXCLUDED.value_primary,
                    tolerance_percent = EXCLUDED.tolerance_percent,
                    power_rating_w = EXCLUDED.power_rating_w,
                    voltage_rating_v = EXCLUDED.voltage_rating_v,
                    package_case = EXCLUDED.package_case,
                    dielectric_type = EXCLUDED.dielectric_type
            """, part_id, 
               specs.get('type'), specs.get('value_primary'), specs.get('tolerance_percent'),
               specs.get('power_rating_w'), specs.get('voltage_rating_v'),
               specs.get('package_case'), specs.get('dielectric_type')
            )

    async def run(self):
        for part in PASSIVE_PARTS:
            await self.ingest_part(part)

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    pool = await asyncpg.create_pool(db_url)
    try:
        ingester = PassiveIngester(pool)
        await ingester.run()
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
