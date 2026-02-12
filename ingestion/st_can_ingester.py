
import asyncio
import asyncpg
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

# ST CAN Families
ST_CAN_FAMILIES = {
    # High Speed CAN
    "L9616": {
        "rate_mbps": 1.0,
        "protocol": "CAN",
        "vin_range": [4.75, 5.25],
        "standby": False,
        "esd_kv": 4.0,
        "variants": [
            {"series": "L9616", "package": ["D", "K"]} # SO-8
        ]
    },
    # Dual Channel / FD Ready
    "L9966": {
        "rate_mbps": 5.0, # FD
        "protocol": "CAN-FD",
        "vin_range": [3.0, 5.25], # 3.3V/5V compatible
        "standby": True,
        "esd_kv": 8.0,
        "variants": [
            {"series": "L9966", "package": ["TR"]} # PowerSSO-12
        ]
    }
}

async def seed_can_parts(conn: asyncpg.Connection):
    total_new = 0
    
    for family, data in ST_CAN_FAMILIES.items():
        logger.info(f"Processing family: {family}")
        
        rate = data["rate_mbps"]
        protocol = data["protocol"]
        vin_min, vin_max = data["vin_range"]
        standby = data.get("standby", False)
        esd = data.get("esd_kv", 2.0)
        
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
                
                # Insert CAN Specs
                await conn.execute("""
                    INSERT INTO can_specs (
                        part_id, 
                        max_data_rate_mbps, protocol_type,
                        supply_voltage_min_v, supply_voltage_max_v,
                        has_standby_mode, esd_protection_kv
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (part_id) DO UPDATE
                    SET max_data_rate_mbps = EXCLUDED.max_data_rate_mbps
                """, part_id, 
                     rate, protocol,
                     vin_min, vin_max,
                     standby, esd)
                
                total_new += 1
                
    logger.info(f"Seeding complete. Processed {total_new} CAN variants.")
    return total_new

async def main():
    try:
        conn = await asyncpg.connect(DB_URL)
        await seed_can_parts(conn)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
