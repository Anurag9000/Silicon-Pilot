
import asyncio
import asyncpg
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL will be initialized in main
DB_URL = None

# ST DC-DC Families (Buck/Boost)
# Identifying popular families to seed
ST_DCDC_FAMILIES = {
    # Synchronous Step-Down (Buck)
    "L6984": {
        "topology": "buck",
        "vin_range": [4.5, 36], # V
        "vout_range": [0.9, 36], # V
        "iout_max": 0.4, # A
        "sync": True,
        "variants": [
            {"series": "L6984", "package": ["TR", "ATR"]} # TR=Tape&Reel
        ]
    },
    "ST1S10": {
        "topology": "buck", 
        "vin_range": [2.5, 18],
        "vout_range": [0.8, 16], # approx
        "iout_max": 3.0,
        "sync": True,
        "variants": [
            {"series": "ST1S10", "package": ["PUR", "PHR"]} # DFN8, SO8
        ]
    },
    # Asynchronous Step-Down
    "L7986": {
        "topology": "buck",
        "vin_range": [4.5, 38],
        "vout_range": [0.6, 38],
        "iout_max": 3.0,
        "sync": False,
        "variants": [
            {"series": "L7986", "package": ["TA", "TR"]}
        ]
    },
    # Boost (Step-Up)
    "L6920": {
        "topology": "boost",
        "vin_range": [0.6, 5.5],
        "vout_range": [1.8, 5.5],
        "iout_max": 0.8, # switch current limit
        "sync": True,
        "variants": [
            {"series": "L6920", "package": ["D", "DB"]}
        ]
    }
}

async def seed_dcdc_parts(conn: asyncpg.Connection):
    total_new = 0
    
    for family, data in ST_DCDC_FAMILIES.items():
        logger.info(f"Processing family: {family}")
        
        topology = data["topology"]
        vin_min, vin_max = data["vin_range"]
        vout_min, vout_max = data["vout_range"]
        iout = data["iout_max"]
        is_sync = data["sync"]
        
        for variant in data["variants"]:
            series = variant["series"]
            for pkg in variant["package"]:
                # Generate MPN
                mpn = f"{series}{pkg}"
                
                # Check/Insert Part
                # Using standard MPN insertion logic
                part_id = await conn.fetchval("""
                    INSERT INTO parts (mpn, manufacturer, family, datasheet_url)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (mpn) DO UPDATE 
                    SET updated_at = NOW()
                    RETURNING id
                """, mpn, "STMicroelectronics", family, 
                     f"https://www.st.com/resource/en/datasheet/{series.lower()}.pdf")
                
                # Insert DC-DC Specs
                await conn.execute("""
                    INSERT INTO dcdc_specs (
                        part_id, topology, is_synchronous,
                        vin_min_v, vin_max_v,
                        vout_min_v, vout_max_v,
                        iout_max_a, num_outputs
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 1)
                    ON CONFLICT (part_id) DO UPDATE
                    SET topology = EXCLUDED.topology
                """, part_id, topology, is_sync, 
                     vin_min, vin_max, vout_min, vout_max, iout)
                
                total_new += 1
                
    logger.info(f"Seeding complete. Processed {total_new} variants.")
    return total_new

async def main():
    global DB_URL
    DB_URL = os.getenv("DATABASE_URL")
    if not DB_URL:
        # Fallback for manual run
        DB_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot"
        
    try:
        conn = await asyncpg.connect(DB_URL)
        await seed_dcdc_parts(conn)
        await conn.close()
    except Exception as e:
        logger.error(f"Failed: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
