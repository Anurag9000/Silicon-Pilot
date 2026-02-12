
import asyncio
import asyncpg
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

# Essential "Golden" Passives for Reference Designs
# We treat these as "Generic" or use placeholders for Manufacturer
ESSENTIAL_PASSIVES = [
    # Resistors (1%)
    {"mpn": "R0402-10K", "type": "Resistor", "val": 10000.0, "fmt": "10k", "pkg": "0402", "tol": 1.0, "pwr": 0.063},
    {"mpn": "R0402-100K", "type": "Resistor", "val": 100000.0, "fmt": "100k", "pkg": "0402", "tol": 1.0, "pwr": 0.063},
    {"mpn": "R0603-1K", "type": "Resistor", "val": 1000.0, "fmt": "1k", "pkg": "0603", "tol": 1.0, "pwr": 0.1},
    {"mpn": "R0603-0R", "type": "Resistor", "val": 0.0, "fmt": "0R", "pkg": "0603", "tol": 0.0, "pwr": 0.1},
    
    # Capacitors (MLCC)
    {"mpn": "C0402-100nF", "type": "Capacitor", "val": 1e-7, "fmt": "100nF", "pkg": "0402", "vol": 16.0, "diel": "X7R"},
    {"mpn": "C0603-1uF", "type": "Capacitor", "val": 1e-6, "fmt": "1uF", "pkg": "0603", "vol": 16.0, "diel": "X7R"},
    {"mpn": "C0603-10uF", "type": "Capacitor", "val": 1e-5, "fmt": "10uF", "pkg": "0603", "vol": 6.3, "diel": "X5R"},
    {"mpn": "C0402-22pF", "type": "Capacitor", "val": 2.2e-11, "fmt": "22pF", "pkg": "0402", "vol": 50.0, "diel": "C0G"},
]

async def seed_passive_parts(conn: asyncpg.Connection):
    total_new = 0
    
    logger.info(f"Seeding {len(ESSENTIAL_PASSIVES)} essential passive components...")
    
    for p in ESSENTIAL_PASSIVES:
        mpn = p["mpn"]
        p_type = p["type"]
        val = p["val"]
        fmt = p["fmt"]
        pkg = p["pkg"]
        
        # Determine manufacturer (Generic)
        mfr = "Generic" 
        
        # Check/Insert Part
        part_id = await conn.fetchval("""
            INSERT INTO parts (mpn, manufacturer, family, datasheet_url)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (mpn) DO UPDATE 
            SET updated_at = NOW()
            RETURNING id
        """, mpn, mfr, p_type, "https://www.digikey.com") # Placeholder URL
        
        # Insert Specs
        if p_type == "Resistor":
            await conn.execute("""
                INSERT INTO passive_specs (
                    part_id, component_type, value_primary, value_formatted,
                    tolerance_percent, power_rating_w, package_case
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (part_id) DO UPDATE
                SET value_primary = EXCLUDED.value_primary
            """, part_id, p_type, val, fmt, p["tol"], p["pwr"], pkg)
            
        elif p_type == "Capacitor":
             await conn.execute("""
                INSERT INTO passive_specs (
                    part_id, component_type, value_primary, value_formatted,
                    voltage_rating_v, dielectric_type, package_case
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (part_id) DO UPDATE
                SET value_primary = EXCLUDED.value_primary
            """, part_id, p_type, val, fmt, p["vol"], p["diel"], pkg)
            
        total_new += 1
                
    logger.info(f"Seeding complete. Processed {total_new} Passive parts.")
    return total_new

async def main():
    try:
        conn = await asyncpg.connect(DB_URL)
        await seed_passive_parts(conn)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
