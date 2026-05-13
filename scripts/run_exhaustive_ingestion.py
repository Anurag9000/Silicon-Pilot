import asyncio
import os
import sys
import uuid
import json
import asyncpg

# Import parts from part1 and part2
sys.path.insert(0, "/home/anurag-basistha/Projects/ToFix/Silicon-Pilot/scripts")
import ingest_all_stm32
import ingest_all_stm32_part2

# Get the list of parts
ALL_PARTS = ingest_all_stm32.PARTS + ingest_all_stm32_part2.get_more_parts(ingest_all_stm32.p)
DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")

async def run_ingestion():
    print(f"Connecting to DB to insert {len(ALL_PARTS)} exhaustive STM32 parts...")
    conn = await asyncpg.connect(DB_URL)
    
    # First, clear the database completely to prevent conflicts
    print("Clearing old data...")
    await conn.execute("TRUNCATE parts CASCADE;")
    
    parts_inserted = 0
    for p in ALL_PARTS:
        # Create part UUID
        part_id = str(uuid.uuid4())
        
        # Insert into parts table
        await conn.execute("""
            INSERT INTO parts (id, mpn, manufacturer, family, package_family, status)
            VALUES ($1, $2, 'STMicroelectronics', $3, $4, $5)
        """, part_id, p['mpn'], p['family'], p['pkg'], p.get('status', 'active'))
        
        # Format extras
        extras = p.get('extras', {})
        extras['url'] = p.get('url', '')
        
        # Insert into mcu_specs table
        await conn.execute("""
            INSERT INTO mcu_specs (
                part_id, core, max_mhz, flash_kb, sram_kb, 
                can_count, can_fd_count, usb_fs, usb_hs,
                uart_count, spi_count, i2c_count, adc_count, dac_count, ethernet_count,
                timers_count, pwm_channels, has_fpu, has_dsp, has_crypto, has_wireless,
                voltage_min_v, voltage_max_v, cost_usd, extras
            ) VALUES (
                $1, $2, $3, $4, $5, 
                $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21,
                $22, $23, $24, $25
            )
        """, 
        part_id, p['core'], p['mhz'], p['flash'], p['sram'],
        p.get('can', 0), p.get('canfd', 0), p.get('usbfs', 0), p.get('usbhs', 0),
        p.get('uart', 0), p.get('spi', 0), p.get('i2c', 0), p.get('adc', 0), p.get('dac', 0), p.get('eth', 0),
        p.get('timers', 0), p.get('pwm', 0), p.get('fpu', 0), p.get('dsp', 0), p.get('crypto', 0), p.get('wireless', 0),
        p.get('vmin'), p.get('vmax'), p.get('cost'), json.dumps(extras)
        )
        parts_inserted += 1
        if parts_inserted % 50 == 0:
            print(f"Inserted {parts_inserted}/{len(ALL_PARTS)}...")
            
    await conn.close()
    print(f"✅ Exhaustive ingestion complete! Inserted {parts_inserted} MCU variations across all STM32 families.")

if __name__ == "__main__":
    asyncio.run(run_ingestion())
