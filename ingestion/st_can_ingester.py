
"""
Ingester for STMicroelectronics CAN Transceivers
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
CAN_FAMILIES = {
    "L9616": {
        "description": "High Speed CAN Bus Transceiver",
        "url": "https://www.st.com/en/automotive-analog-and-power/l9616.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/l9616.pdf",
        "specs": {
            "data_rate_mbps": 1.0,
            "supply_voltage_min_v": 4.5,
            "supply_voltage_max_v": 5.5,
            "has_standby_mode": False,
            "has_wakeup_mode": False,
            "protection_esd_kv": 4.0,
            "automotive_grade": True,
            "package_type": "SO-8"
        }
    },
    "L9966": {
        "description": "Automotive Multi-Channel CAN Transceiver",
        "url": "https://www.st.com/en/automotive-analog-and-power/l9966.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/l9966.pdf",
        "specs": {
            "data_rate_mbps": 5.0, # CAN FD capable
            "supply_voltage_min_v": 3.0, # 3.3V compatible
            "supply_voltage_max_v": 5.5,
            "has_standby_mode": True,
            "has_wakeup_mode": True,
            "protection_esd_kv": 8.0,
            "automotive_grade": True,
            "package_type": "QFN-48"
        }
    }
}

class CANIngester:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def ingest_family(self, family_name: str, data: dict):
        """Ingest a CAN family and its specs"""
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
                INSERT INTO can_specs (
                    part_id, data_rate_mbps, supply_voltage_min_v, supply_voltage_max_v,
                    has_standby_mode, has_wakeup_mode, protection_esd_kv, 
                    automotive_grade, package_type
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (part_id) DO UPDATE SET
                    data_rate_mbps = EXCLUDED.data_rate_mbps,
                    supply_voltage_min_v = EXCLUDED.supply_voltage_min_v,
                    supply_voltage_max_v = EXCLUDED.supply_voltage_max_v,
                    has_standby_mode = EXCLUDED.has_standby_mode,
                    has_wakeup_mode = EXCLUDED.has_wakeup_mode,
                    protection_esd_kv = EXCLUDED.protection_esd_kv,
                    automotive_grade = EXCLUDED.automotive_grade,
                    package_type = EXCLUDED.package_type
            """, part_id, 
               specs.get('data_rate_mbps'), specs.get('supply_voltage_min_v'), specs.get('supply_voltage_max_v'),
               specs.get('has_standby_mode'), specs.get('has_wakeup_mode'),
               specs.get('protection_esd_kv'), specs.get('automotive_grade'),
               specs.get('package_type')
            )

    async def run(self):
        for family, data in CAN_FAMILIES.items():
            await self.ingest_family(family, data)

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    pool = await asyncpg.create_pool(db_url)
    try:
        ingester = CANIngester(pool)
        await ingester.run()
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
