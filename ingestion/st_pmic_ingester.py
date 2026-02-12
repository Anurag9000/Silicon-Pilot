
"""
Ingester for STMicroelectronics PMICs
"""

import asyncio
import logging
import asyncpg
import os
import re
from typing import List, Dict, Optional
from datetime import datetime
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target families
PMIC_FAMILIES = {
    "STPMIC1": {
        "description": "Power Management IC for STM32MP1",
        "url": "https://www.st.com/en/power-management/stpmic1.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/stpmic1.pdf",
        "specs": {
            "input_voltage_min_v": 2.8,
            "input_voltage_max_v": 5.5,
            "output_count": 14,
            "buck_count": 4,
            "ldo_count": 6,
            "boost_count": 1,
            "control_interface": ["I2C"],
            "automotive_grade": True
        }
    },
    "L4995": {
        "description": "Automotive 5V Low Drop Voltage Regulator with Watchdog",
        "url": "https://www.st.com/en/automotive-analog-and-power/l4995.html",
        "datasheet": "https://www.st.com/resource/en/datasheet/l4995.pdf",
        "specs": {
            "input_voltage_min_v": 5.6,
            "input_voltage_max_v": 31.0,
            "output_count": 1,
            "ldo_count": 1,
            "control_interface": [],
            "automotive_grade": True
        }
    }
}

class PMICIngester:
    def __init__(self, db_pool):
        self.db_pool = db_pool

    async def ingest_family(self, family_name: str, data: dict):
        """Ingest a PMIC family and its specs"""
        logger.info(f"Ingesting family: {family_name}")
        
        async with self.db_pool.acquire() as conn:
            # 1. Insert into parts table
            # For PMICs, the family name is often the root part number
            mpn = family_name 
            
            # Check if exists
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
            
            # 2. Insert into pmic_specs
            specs = data['specs']
            await conn.execute("""
                INSERT INTO pmic_specs (
                    part_id, input_voltage_min_v, input_voltage_max_v, 
                    output_count, buck_count, ldo_count, boost_count,
                    control_interface, automotive_grade
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (part_id) DO UPDATE SET
                    input_voltage_min_v = EXCLUDED.input_voltage_min_v,
                    input_voltage_max_v = EXCLUDED.input_voltage_max_v,
                    output_count = EXCLUDED.output_count,
                    buck_count = EXCLUDED.buck_count,
                    ldo_count = EXCLUDED.ldo_count,
                    boost_count = EXCLUDED.boost_count,
                    control_interface = EXCLUDED.control_interface,
                    automotive_grade = EXCLUDED.automotive_grade
            """, part_id, 
               specs.get('input_voltage_min_v'), specs.get('input_voltage_max_v'),
               specs.get('output_count'), specs.get('buck_count', 0), 
               specs.get('ldo_count', 0), specs.get('boost_count', 0),
               specs.get('control_interface', []), specs.get('automotive_grade', False)
            )

    async def run(self):
        """Run ingestion for all defined families"""
        for family, data in PMIC_FAMILIES.items():
            await self.ingest_family(family, data)

async def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"
    pool = await asyncpg.create_pool(db_url)
    
    try:
        ingester = PMICIngester(pool)
        await ingester.run()
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
