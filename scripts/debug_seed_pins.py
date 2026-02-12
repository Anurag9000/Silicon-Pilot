
import asyncio
import asyncpg
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugSeed")

async def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    pool = await asyncpg.create_pool(db_url)
    
    try:
        async with pool.acquire() as conn:
            # 1. Check Schema
            schema = await conn.fetchval("SELECT current_schema()")
            logger.info(f"Current Schema: {schema}")
            
            # 2. Check Table Existence
            regclass = await conn.fetchval("SELECT to_regclass('mcu_pin_functions')")
            logger.info(f"to_regclass('mcu_pin_functions'): {regclass}")
            
            # 3. Create Table explicitly in public
            logger.info("Creating table public.mcu_pin_functions...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS public.mcu_pin_functions (
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
            
            # 4. Check Existence Again
            regclass_after = await conn.fetchval("SELECT to_regclass('public.mcu_pin_functions')")
            logger.info(f"to_regclass('public.mcu_pin_functions') after create: {regclass_after}")

            # 5. Insert Dummy Data
            row = await conn.fetchrow("SELECT id FROM parts WHERE mpn LIKE 'STM32F4%' LIMIT 1")
            if row:
                part_id = row['id']
                logger.info(f"Target Part: {part_id}")
                await conn.execute("DELETE FROM public.mcu_pin_functions WHERE part_id = $1", part_id)
                await conn.execute("""
                    INSERT INTO public.mcu_pin_functions (part_id, pin_number, pin_name, af7_function, is_power_pin)
                    VALUES ($1, 1, 'PA9', 'USART1_TX', FALSE)
                """, part_id)
                logger.info("Inserted PA9")
            else:
                logger.error("No part found")

    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
