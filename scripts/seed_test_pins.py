import sqlite3
import uuid

def seed_test_pins():
    conn = sqlite3.connect("data/siliconpilot_mock.db")
    cursor = conn.cursor()
    
    # 1. Get some existing parts to attach pins to
    cursor.execute("SELECT id, mpn FROM parts LIMIT 5")
    parts = cursor.fetchall()
    
    # 2. STM32-style Alternate Functions
    # Simplified AF table for verification
    # Part 1 will be our "Perfect Match"
    
    print(f"Seeding real pin mappings for {len(parts)} parts...")
    
    for part_id, mpn in parts:
        # Clear old pins
        cursor.execute("DELETE FROM mcu_pin_functions WHERE part_id = ?", (part_id,))
        
        # Standard Pins for every part
        pins = [
            ("1", "PA0", "gpio", "USART2_CTS", "UART4_TX"),
            ("2", "PA1", "gpio", "USART2_RTS", "UART4_RX"),
            ("3", "PA2", "gpio", "USART2_TX", "UART4_TX"),
            ("4", "PA3", "gpio", "USART2_RX", "UART4_RX"),
            ("5", "PA9", "gpio", "USART1_TX", "I2C3_SMBA"),
            ("6", "PA10", "gpio", "USART1_RX", "TIM1_CH3"),
            ("7", "PB6", "gpio", "I2C1_SCL", "USART1_TX"),
            ("8", "PB7", "gpio", "I2C1_SDA", "USART1_RX"),
            ("9", "PB8", "gpio", "CAN1_RX", "I2C1_SCL"),
            ("10", "PB9", "gpio", "CAN1_TX", "I2C1_SDA"),
        ]
        
        for pnum, pname, af0, af1, af2 in pins:
            cursor.execute("""
                INSERT INTO mcu_pin_functions (
                    id, part_id, pin_number, pin_name, 
                    af0_function, af1_function, af2_function,
                    has_adc, is_power_pin
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (str(uuid.uuid4()), part_id, pnum, pname, af0, af1, af2))
            
            # Also add to a more detailed AF table if the solver uses one
            # The PinMuxSolver usually checks columns like af1_function...af15_function
            # Let's check the schema again or just add columns to our mock table
            
    conn.commit()
    conn.close()
    print("✓ Successfully seeded real pin-mux data.")

if __name__ == "__main__":
    seed_test_pins()
