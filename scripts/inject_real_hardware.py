import sqlite3
import uuid
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def force_inject_real_hardware():
    # 1. Inject into SQLite (Mock)
    sqlite_conn = sqlite3.connect("data/hardwaregenius_mock.db")
    inject_to_db(sqlite_conn, "sqlite")
    sqlite_conn.close()
    
    # 2. Inject into PostgreSQL (Real)
    pg_url = os.getenv("REAL_DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
    try:
        pg_conn = psycopg2.connect(pg_url)
        inject_to_db(pg_conn, "postgres")
        pg_conn.close()
        print("✓ Real hardware injected into BOTH SQLite and PostgreSQL.")
    except Exception as e:
        print(f"⚠ Skipping PostgreSQL injection: {e}")

def inject_to_db(conn, db_type):
    cursor = conn.cursor()
    placeholder = "?" if db_type == "sqlite" else "%s"
    
    part_id = str(uuid.uuid4())
    mpn = "STM32H743VIT6"
    
    # Delete old
    cursor.execute(f"DELETE FROM parts WHERE mpn = {placeholder}", (mpn,))
    
    # Insert Part
    cursor.execute(f"""
        INSERT INTO parts (id, mpn, manufacturer, family, status, datasheet_url, package_name, pin_count, theta_ja_c_w)
        VALUES ({','.join([placeholder]*9)})
    """, (part_id, mpn, 'STMicroelectronics', 'STM32H7', 'active', 'https://www.st.com/resource/en/datasheet/stm32h743vi.pdf', 'LQFP100', 100, 42.5))
    
    # Insert Specs
    cursor.execute(f"DELETE FROM mcu_specs WHERE part_id = {placeholder}", (part_id,))
    cursor.execute(f"""
        INSERT INTO mcu_specs (
            id, part_id, core, max_mhz, flash_kb, sram_kb, ram_kb,
            can_count, uart_count, spi_count, i2c_count, adc_channels,
            has_fpu, has_dsp, cost_usd
        ) VALUES ({','.join([placeholder]*15)})
    """, (str(uuid.uuid4()), part_id, 'Cortex-M7', 480, 2048, 1024, 1024, 2, 8, 6, 4, 24, 1, 1, 9.50))
    
    # Insert Pins
    cursor.execute(f"DELETE FROM mcu_pin_functions WHERE part_id = {placeholder}", (part_id,))
    pins = [
        ("1", "PA9", "gpio", "USART1_TX", "CAN1_TX"),
        ("2", "PA10", "gpio", "USART1_RX", "CAN1_RX"),
        ("3", "PB8", "gpio", "CAN1_RX", "I2C1_SCL"),
        ("4", "PB9", "gpio", "CAN1_TX", "I2C1_SDA"),
    ]
    for pnum, pname, af0, af1, af2 in pins:
        cursor.execute(f"""
            INSERT INTO mcu_pin_functions (id, part_id, pin_number, pin_name, af0_function, af1_function, af2_function)
            VALUES ({','.join([placeholder]*7)})
        """, (str(uuid.uuid4()), part_id, pnum, pname, af0, af1, af2))

    conn.commit()
    cursor.close()

if __name__ == "__main__":
    force_inject_real_hardware()
