
import asyncio
import asyncpg
import uuid
import os
from typing import List

# Mock matcher import (assuming it's in path or we adjust path)
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from architecture.reference_design_matcher import ReferenceDesignMatcher

async def test_matcher():
    print("Testing Reference Design Matcher...")
    
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
    matcher = ReferenceDesignMatcher(db_url)
    conn = await asyncpg.connect(db_url)
    
    try:
        # 1. Setup Data: Get an MCU
        mcu_id = await conn.fetchval("SELECT part_id FROM mcu_specs LIMIT 1")
        if not mcu_id:
            print("No MCUs found in DB. Skipping test.")
            return

        mcu_details = await conn.fetchrow("""
            SELECT p.mpn, p.family, m.core 
            FROM parts p JOIN mcu_specs m ON p.id = m.part_id 
            WHERE p.id = $1
        """, mcu_id)
        print(f"Target MCU: {mcu_details['mpn']} ({mcu_details['family']}/{mcu_details['core']})")

        # 2. Create a Mock Reference Design if none exists
        # We'll create one that matches exact, and one that is just same series
        
        # Exact Match Design
        d1_id = await matcher.add_reference_design(
            design_name="Test Design Exact",
            manufacturer="ST",
            application_area="Motor Control",
            description="Exact match",
            schematic_url="http://example.com/schem1"
        )
        # Add the MCU to it
        await matcher.add_design_part(d1_id, mcu_id, "U1", 1, is_critical=True)
        print(f"Created/Using Design 1 (Exact): {d1_id}")

        # Series Match Design (Need another MCU of same series/core but diff MPN)
        # For simplicity, we just check if finding D1 works first
        
        # 3. Test find_similar_designs
        print("\nRunning find_similar_designs...")
        matches = await matcher.find_similar_designs(mcu_id, user_application="Motor")
        
        found_exact = False
        for m in matches:
            print(f"Match: {m.design_name} | Score: {m.match_score} | Reasons: {m.match_reasons}")
            if m.design_id == d1_id:
                found_exact = True
                if m.match_score >= 80: # 50 (MCU) + 30 (App) + 20 (Docs) -> 100 max
                     print("[OK] Score looks reasonable")
                else:
                     print(f"[WARN] Score {m.match_score} might be low")

        if found_exact:
            print("[OK] Exact match design found")
        else:
            print("[FAIL] Exact match design NOT found")
            
        # Cleanup (Optional, or leave for persistent debugging)
        # await conn.execute("DELETE FROM reference_designs WHERE id = $1", d1_id)

    finally:
        await conn.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_matcher())
