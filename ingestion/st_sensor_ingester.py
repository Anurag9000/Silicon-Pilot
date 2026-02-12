
"""
Ingester for STMicroelectronics Sensors (MEMS, Temp, etc.)
"""

import asyncio
import logging
import asyncpg
import os
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target families
SENSOR_FAMILIES = {
    "LIS2DH12": {
        "description": "Ultra-low-power high-performance 3-axis accelerometer",
        "url": "https://www.st.com/en/mems-and-sensors/lis2dh12.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/lis2dh12.pdf",
        "specs": {
            "sensor_type": "Accelerometer",
            "interface": ["I2C", "SPI"],
            "supply_voltage_min_v": 1.71,
            "supply_voltage_max_v": 3.6,
            "resolution_bits": 12,
            "sampling_rate_hz": 5300.0,
            "package_type": "LGA-12",
            "automotive_grade": False
        }
    },
    "STTS751": {
        "description": "2.25 V low-voltage local digital temperature sensor",
        "url": "https://www.st.com/en/mems-and-sensors/stts751.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/stts751.pdf",
        "specs": {
            "sensor_type": "Temperature",
            "interface": ["I2C", "SMBus"],
            "supply_voltage_min_v": 2.25,
            "supply_voltage_max_v": 3.6,
            "resolution_bits": 12,
            "sampling_rate_hz": 10.0, # Programmable
            "package_type": "UDFN-6",
            "automotive_grade": False
        }
    }
}

class SensorIngester:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def ingest_family(self, family_name: str, data: dict):
        """Ingest a Sensor family and its specs"""
        logger.info(f"Ingesting family: {family_name}")
        
        async with self.db_pool.acquire() as conn:
            mpn = family_name 
            
            # 1. Upsert Part
            part_id = await conn.fetchval("SELECT id FROM parts WHERE mpn = $1", mpn)
            
            if not part_id:
                part_id = uuid.uuid4()
                await conn.execute("""
                    INSERT INTO parts (id, mpn, manufacturer, family, description, datasheet_url, status)
                    VALUES ($1, $2, 'STMicroelectronics', $3, $4, $5, 'active')
                """, part_id, mpn, family_name, data['description'], data['datasheet'])
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
                INSERT INTO sensor_specs (
                    part_id, sensor_type, interface, 
                    supply_voltage_min_v, supply_voltage_max_v,
                    resolution_bits, sampling_rate_hz,
                    package_type, automotive_grade
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (part_id) DO UPDATE SET
                    sensor_type = EXCLUDED.sensor_type,
                    interface = EXCLUDED.interface,
                    supply_voltage_min_v = EXCLUDED.supply_voltage_min_v,
                    supply_voltage_max_v = EXCLUDED.supply_voltage_max_v,
                    resolution_bits = EXCLUDED.resolution_bits,
                    sampling_rate_hz = EXCLUDED.sampling_rate_hz,
                    package_type = EXCLUDED.package_type,
                    automotive_grade = EXCLUDED.automotive_grade
            """, part_id, 
               specs.get('sensor_type'), specs.get('interface'),
               specs.get('supply_voltage_min_v'), specs.get('supply_voltage_max_v'),
               specs.get('resolution_bits'), specs.get('sampling_rate_hz'),
               specs.get('package_type'), specs.get('automotive_grade')
            )

    async def run(self):
        for family, data in SENSOR_FAMILIES.items():
            await self.ingest_family(family, data)

async def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    pool = await asyncpg.create_pool(db_url)
    try:
        ingester = SensorIngester(pool)
        await ingester.run()
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
