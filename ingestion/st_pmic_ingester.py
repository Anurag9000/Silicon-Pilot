
import asyncio
import asyncpg
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

# ST PMIC Families
ST_PMIC_FAMILIES = {
    # MPU Power Management
    "STPMIC1": {
        "buck_count": 4,
        "ldo_count": 6,
        "boost_count": 1,
        "vin_range": [2.8, 5.5],
        "interface": "I2C",
        "automotive": False,
        "variants": [
            {"series": "STPMIC1", "package": ["APQR", "BPQR"]} # WFQFN 44
        ]
    },
    # Automotive Power Management
    "L4995": {
        "buck_count": 0,
        "ldo_count": 1, # 5V Regulator
        "boost_count": 0,
        "vin_range": [5.6, 31],
        "interface": "None",
        "automotive": True,
        "watchdog": True,
        "variants": [
            {"series": "L4995", "package": ["J", "K"]} # PowerSSO-12
        ]
    }
}

async def seed_pmic_parts(conn: asyncpg.Connection):
    total_new = 0
    
    for family, data in ST_PMIC_FAMILIES.items():
        logger.info(f"Processing family: {family}")
        
        buck_count = data["buck_count"]
        ldo_count = data["ldo_count"]
        boost_count = data["boost_count"]
        vin_min, vin_max = data["vin_range"]
        interface = data["interface"]
        automotive = data.get("automotive", False)
        watchdog = data.get("watchdog", False)
        
        for variant in data["variants"]:
            series = variant["series"]
            for pkg in variant["package"]:
                # Generate MPN
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
                
                # Insert PMIC Specs
                await conn.execute("""
                    INSERT INTO pmic_specs (
                        part_id, 
                        buck_count, ldo_count, boost_count,
                        has_buck, has_ldo, has_boost,
                        vin_min_v, vin_max_v,
                        interface_type, is_automotive, has_watchdog
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ON CONFLICT (part_id) DO UPDATE
                    SET buck_count = EXCLUDED.buck_count
                """, part_id, 
                     buck_count, ldo_count, boost_count,
                     buck_count > 0, ldo_count > 0, boost_count > 0,
                     vin_min, vin_max,
                     interface, automotive, watchdog)
                
                total_new += 1
                
    logger.info(f"Seeding complete. Processed {total_new} PMIC variants.")
    return total_new

async def main():
    try:
        conn = await asyncpg.connect(DB_URL)
        await seed_pmic_parts(conn)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
