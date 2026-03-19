import os
import asyncio
import uuid
import random
from datetime import datetime, timedelta
from core.mock_database import get_mock_db

# High-Fidelity Mock Data Generation
# Schema-compliant, handles edge cases, maintains referential integrity

MANUFACTURERS = ["STMicroelectronics", "Espressif", "Nordic Semiconductor", "Texas Instruments", "Microchip", "NXP"]
CORES = ["Cortex-M0", "Cortex-M0+", "Cortex-M3", "Cortex-M4", "Cortex-M7", "Cortex-M33", "RISC-V", "Xtensa LX7"]
PACKAGES = ["LQFP-32", "LQFP-48", "LQFP-64", "LQFP-100", "QFN-32", "QFN-48", "BGA-100", "WLCSP-25"]

async def generate_data(num_parts=100):
    db = get_mock_db()
    cursor = db.conn.cursor()
    
    print(f"Generating {num_parts} high-fidelity parts...")
    
    parts_data = []
    mcu_specs_data = []
    
    for i in range(num_parts):
        part_id = str(uuid.uuid4())
        mfg = random.choice(MANUFACTURERS)
        family = f"{mfg[:2].upper()}{random.randint(10, 99)}"
        mpn = f"{family}{random.choice(['F', 'G', 'L', 'H'])}{random.randint(100, 999)}{random.choice(['R', 'V', 'Z'])}{random.choice(['6', '7', 'T'])}"
        
        # Randomly include nulls/edge cases
        package_family = random.choice(PACKAGES).split('-')[0]
        package_name = random.choice(PACKAGES)
        pin_count = int(package_name.split('-')[1])
        
        status = 'active'
        if i % 20 == 0: status = 'deprecated'
        if i % 50 == 0: status = 'discontinued'
        
        created_at = (datetime.now() - timedelta(days=random.randint(1, 1000))).isoformat()
        
        # Insert into parts
        cursor.execute(
            "INSERT INTO parts (id, mpn, manufacturer, family, status, package_family, package_name, pin_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (part_id, mpn, mfg, family, status, package_family, package_name, pin_count, created_at)
        )
        
        # Generate MCU Specs
        spec_id = str(uuid.uuid4())
        core = random.choice(CORES)
        max_mhz = random.choice([16, 32, 48, 64, 72, 80, 100, 120, 168, 216, 400, 480])
        flash_kb = random.choice([16, 32, 64, 128, 256, 512, 1024, 2048])
        sram_kb = flash_kb // random.choice([2, 4, 8])
        ram_kb = sram_kb
        
        # Edge case: High outliers
        if i == 0:
            flash_kb = 16384
            ram_kb = 4096
            max_mhz = 1000
            
        # Edge case: Low outliers
        if i == 1:
            flash_kb = 4
            ram_kb = 1
            max_mhz = 1
            
        cursor.execute("""
            INSERT INTO mcu_specs (
                id, part_id, core, max_mhz, flash_kb, ram_kb, 
                can_count, uart_count, spi_count, i2c_count, 
                adc_channels, has_fpu, vdd_min_v, vdd_max_v, 
                active_ma, standby_ua, cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            spec_id, part_id, core, max_mhz, flash_kb, ram_kb,
            random.randint(0, 3), random.randint(1, 8), random.randint(1, 6), random.randint(1, 6),
            random.randint(0, 24), random.choice([0, 1]), 1.71, 3.6,
            round(random.uniform(0.1, 50.0), 2), round(random.uniform(0.5, 10.0), 2),
            round(random.uniform(0.5, 15.0), 2)
        ))

    db.conn.commit()
    print("✓ Successfully populated high-fidelity mock data.")
    db.close()

if __name__ == "__main__":
    asyncio.run(generate_data(100))
