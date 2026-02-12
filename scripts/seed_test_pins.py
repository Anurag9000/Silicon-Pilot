
import asyncio
import asyncpg
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedPins")

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    pool = await asyncpg.create_pool(db_url)
    
    try:
        async with pool.acquire() as conn:
            # 1. Find Part
            row = await conn.fetchrow("SELECT id FROM parts WHERE mpn LIKE 'STM32F4%' LIMIT 1")
            if not row:
                logger.error("No STM32F4 part found!")
                return
            
            part_id = row['id']
            logger.info(f"Seeding pins for part_id: {part_id}")
            
            # Ensure table exists (since apply_sql might have failed silently or phantomly)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS mcu_pin_functions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    part_id UUID REFERENCES parts(id) ON DELETE CASCADE,
                    pin_number INTEGER NOT NULL,
                    pin_name VARCHAR(50) NOT NULL,
                    af0_function VARCHAR(100), af1_function VARCHAR(100), af2_function VARCHAR(100), af3_function VARCHAR(100),
                    af4_function VARCHAR(100), af5_function VARCHAR(100), af6_function VARCHAR(100), af7_function VARCHAR(100),
                    af8_function VARCHAR(100), af9_function VARCHAR(100), af10_function VARCHAR(100), af11_function VARCHAR(100),
                    af12_function VARCHAR(100), af13_function VARCHAR(100), af14_function VARCHAR(100), af15_function VARCHAR(100),
                    max_current_ma INTEGER,
                    voltage_tolerance VARCHAR(50),
                    is_power_pin BOOLEAN DEFAULT FALSE,
                    is_boot_pin BOOLEAN DEFAULT FALSE,
                    has_adc BOOLEAN DEFAULT FALSE,
                    has_dac BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # 2. Delete existing pins
            await conn.execute("DELETE FROM mcu_pin_functions WHERE part_id = $1", part_id)
            
            # 3. Insert Dummy Pins
            pins = [
                # UART1
                (1, "PA9", "USART1_TX", 7), # AF7 is typically UART
                (2, "PA10", "USART1_RX", 7),
                # Power
                (3, "VDD", None, None),
                (4, "VSS", None, None),
            ]
            
            for pin_num, name, func, af in pins:
                # Construct dynamic update for AF columns
                cols = ["part_id", "pin_number", "pin_name", "type"]
                vals = [part_id, pin_num, name, "IO" if func else "POWER"]
                placeholders = ["$1", "$2", "$3", "$4"]
                
                if func:
                    cols.append(f"af{af}_function")
                    vals.append(func)
                    placeholders.append(f"${len(vals)}")
                
                if name in ["VDD", "VSS"]:
                     cols.append("is_power_pin")
                     vals.append(True)
                     placeholders.append(f"${len(vals)}")
                
                q = f"""
                    INSERT INTO mcu_pin_functions ({', '.join(cols)})
                    VALUES ({', '.join(placeholders)})
                """
                await conn.execute(q, *vals)
                
            logger.info("Pins seeded successfully.")
            
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
