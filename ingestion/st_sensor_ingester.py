
import asyncio
import asyncpg
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

# ST Sensor Families
ST_SENSOR_FAMILIES = {
    # MEMS Accelerometer
    "LIS2DH12": {
        "type": "Accelerometer",
        "interface": "I2C/SPI",
        "vin_range": [1.71, 3.6],
        "current_ua": 2.0, # Low power mode
        "resolution": 12,
        "odr_max": 5300.0,
        "range": "±2g/±4g/±8g/±16g",
        "package": "LGA-12",
        "variants": [
            {"series": "LIS2DH12", "package": ["TR"]}
        ]
    },
    # Temperature Sensor
    "STTS751": {
        "type": "Temperature",
        "interface": "I2C/SMBus",
        "vin_range": [2.25, 3.6],
        "current_ua": 20.0,
        "resolution": 12,
        "odr_max": 32.0, # Conversions per sec
        "range": "-40°C to +125°C",
        "package": "UDFN-6",
        "variants": [
            {"series": "STTS751", "package": ["0WB3F", "1WB3F"]}
        ]
    }
}

async def seed_sensor_parts(conn: asyncpg.Connection):
    total_new = 0
    
    for family, data in ST_SENSOR_FAMILIES.items():
        logger.info(f"Processing family: {family}")
        
        s_type = data["type"]
        interface = data["interface"]
        vin_min, vin_max = data["vin_range"]
        current = data["current_ua"]
        res = data["resolution"]
        odr = data["odr_max"]
        m_range = data["range"]
        pkg_type = data["package"]
        
        for variant in data["variants"]:
            series = variant["series"]
            for pkg in variant["package"]:
                mpn = f"{series}{pkg}"
                
                # Check/Insert Part
                part_id = await conn.fetchval("""
                    INSERT INTO parts (mpn, manufacturer, family, datasheet_url)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (mpn) DO UPDATE 
                    SET updated_at = NOW()
                    RETURNING id
                """, mpn, "STMicroelectronics", family, 
                     f"https://www.st.com/resource/en/datasheet/{series.lower()}.pdf")
                
                # Insert Sensor Specs
                await conn.execute("""
                    INSERT INTO sensor_specs (
                        part_id, 
                        sensor_type, interface_type,
                        supply_voltage_min_v, supply_voltage_max_v,
                        current_consumption_ua, resolution_bits,
                        output_rate_max_hz, measurement_range, package_type
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (part_id) DO UPDATE
                    SET sensor_type = EXCLUDED.sensor_type
                """, part_id, 
                     s_type, interface,
                     vin_min, vin_max,
                     current, res,
                     odr, m_range, pkg_type)
                
                total_new += 1
                
    logger.info(f"Seeding complete. Processed {total_new} Sensor variants.")
    return total_new

async def main():
    try:
        conn = await asyncpg.connect(DB_URL)
        await seed_sensor_parts(conn)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
