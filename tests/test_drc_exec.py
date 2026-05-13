
import asyncio
import asyncpg
import os
import uuid
import sys
from pathlib import Path

# Add project root to python path
sys.path.append(str(Path(__file__).parent.parent))

from solver.design_rule_checker import DesignRuleChecker, Severity

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")

async def test_drc_execution():
    print(f"Connecting to {DB_URL}...")
    conn = await asyncpg.connect(DB_URL)
    
    try:
        # 1. Fetch some real parts to form a "Design"
        print("Fetching parts for test design...")
        
        # Get an MCU with CAN
        mcu_id = await conn.fetchval("""
            SELECT p.id FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE m.can_count > 0
            LIMIT 1
        """)
        
        # Get a PMIC
        pmic_id = await conn.fetchval("""
            SELECT p.id FROM parts p
            JOIN pmic_specs pm ON p.id = pm.part_id
            LIMIT 1
        """)
        
        # Get a CAN Transceiver
        can_id = await conn.fetchval("""
            SELECT p.id FROM parts p
            JOIN can_specs c ON p.id = c.part_id
            LIMIT 1
        """)
        
        if not mcu_id:
            # Fallback: Get ANY MCU and force enable CAN for testing
            print("No CAN MCU found. Picking random MCU and enabling CAN...")
            # Use mcu_specs join to find an MCU
            mcu_id = await conn.fetchval("""
                SELECT p.id FROM parts p 
                JOIN mcu_specs m ON p.id = m.part_id 
                LIMIT 1
            """)
            
            if mcu_id:
                await conn.execute("UPDATE mcu_specs SET can_count = 1 WHERE part_id = $1", mcu_id)
                print(f"Forced CAN=1 on MCU {mcu_id}")
        
        # Always force test conditions on the MCU to ensure violations trigger
        if mcu_id:
             await conn.execute("""
                UPDATE mcu_specs 
                SET can_count = 1, i2c_count = 1, flash_kb = 16, sram_kb = 2
                WHERE part_id = $1
            """, mcu_id)
             print(f"Forced Test Conditions (CAN=1, I2C=1, Flash=16KB) on MCU {mcu_id}")
        
        # Get a PMIC

        design_parts = [mcu_id]
        if pmic_id: design_parts.append(pmic_id)
        if can_id: design_parts.append(can_id)
        
        print(f"Design Parts: {design_parts}")
        
        # 2. Run DRC
        checker = DesignRuleChecker(DB_URL)
        design_uuid = uuid.uuid4()
        
        print(f"\nRunning DRC for Design {design_uuid}...")
        result = await checker.check_design(
            design_parts=design_parts,
            design_id=design_uuid,
            pmic_id=pmic_id
        )
        
        # 3. Print Results
        print("\n--- DRC Results ---")
        summary = result['summary']
        print(f"Total: {summary['total']} | Errors: {summary['errors']} | Warnings: {summary['warnings']}")
        
        for v in result['violations']:
            # Replace special chars for Windows console
            safe_msg = v.message.replace('Ω', 'ohm').replace('µ', 'u')
            print(f"[{v.severity.value.upper()}] {v.rule_name}: {safe_msg}")
            
        # 4. Verify Persistence
        print("\nVerifying Persistence...")
        saved_count = await conn.fetchval("""
            SELECT COUNT(*) FROM drc_violations WHERE design_id = $1
        """, design_uuid)
        
        print(f"Saved records in DB: {saved_count}")
        
        if saved_count == summary['total']:
            print("[OK] Persistence Check Passed")
        else:
            print("[FAIL] Persistence Check Failed")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_drc_execution())
