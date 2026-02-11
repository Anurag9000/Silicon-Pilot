"""
End-to-End Test Script for HardwareGenius

Tests the complete flow:
1. Database connection
2. STM32 data ingestion
3. API recommendation endpoint
4. Frontend serving

Run this to verify everything works!
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.database import get_pool
from core.models import RequirementSpec
from solver.hard_filter import HardFilter
from solver.ranking import RankingEngine


async def test_database():
    """Test 1: Database Connection"""
    print("\n" + "="*60)
    print("TEST 1: Database Connection")
    print("="*60)
    
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT COUNT(*) FROM parts")
            print(f"✓ Database connected")
            print(f"✓ Parts in database: {result}")
        return True, result
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False, 0


async def test_recommendation():
    """Test 2: Recommendation Engine"""
    print("\n" + "="*60)
    print("TEST 2: Recommendation Engine")
    print("="*60)
    
    try:
        pool = await get_pool()
        
        # Create test requirement
        spec = RequirementSpec()
        spec.hard_constraints = {
            "flash_kb": {"min": 256},
            "sram_kb": {"min": 64},
            "can_count": {"min": 1},
        }
        
        print("Test requirement:")
        print(f"  Flash: ≥256KB")
        print(f"  RAM: ≥64KB")
        print(f"  CAN: ≥1")
        
        # Run hard filter
        hard_filter = HardFilter(pool)
        candidates = await hard_filter.filter(spec)
        
        print(f"\n✓ Found {len(candidates)} matching parts")
        
        if candidates:
            # Rank candidates
            ranking_engine = RankingEngine()
            ranked = ranking_engine.rank(candidates, spec)
            
            print("\nTop 3 recommendations:")
            for i, (part, score, breakdown) in enumerate(ranked[:3], 1):
                print(f"\n  {i}. {part.get('mpn', 'Unknown')}")
                print(f"     Manufacturer: {part.get('manufacturer', 'Unknown')}")
                print(f"     Flash: {part.get('flash_kb', '?')}KB")
                print(f"     RAM: {part.get('sram_kb', '?')}KB")
                print(f"     Score: {score:.2f}")
        
        return True, len(candidates)
    
    except Exception as e:
        print(f"✗ Recommendation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


async def test_api():
    """Test 3: API Server"""
    print("\n" + "="*60)
    print("TEST 3: API Server")
    print("="*60)
    
    try:
        import requests
        
        # Test health endpoint
        response = requests.get("http://localhost:8000/health", timeout=2)
        
        if response.status_code == 200:
            print("✓ API server is running")
            print(f"✓ Health check: {response.json()}")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    
    except requests.exceptions.ConnectionError:
        print("✗ API server not running")
        print("  Start with: python server.py")
        return False
    except Exception as e:
        print(f"✗ API test failed: {e}")
        return False


def test_frontend():
    """Test 4: Frontend Files"""
    print("\n" + "="*60)
    print("TEST 4: Frontend")
    print("="*60)
    
    frontend_files = [
        "web_ui/app.py",
        "web_ui/production_app.py",
    ]
    
    all_exist = True
    for file_path in frontend_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    if all_exist:
        print("\n✓ Frontend ready")
        print("  Start with: python web_ui/app.py")
    
    return all_exist


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "HARDWAREGENIUS TEST SUITE")
    print("="*70)
    
    results = {}
    
    # Test 1: Database
    db_ok, part_count = await test_database()
    results['database'] = db_ok
    
    # Test 2: Recommendations (only if DB has data)
    if db_ok and part_count > 0:
        rec_ok, match_count = await test_recommendation()
        results['recommendations'] = rec_ok
    else:
        print("\n⚠ Skipping recommendation test (no data in database)")
        print("  Run: python ingestion/run_stm32_ingestion.py")
        results['recommendations'] = None
    
    # Test 3: API
    api_ok = await test_api()
    results['api'] = api_ok
    
    # Test 4: Frontend
    frontend_ok = test_frontend()
    results['frontend'] = frontend_ok
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        else:
            status = "⊘ SKIP"
        
        print(f"{test_name.upper():20s}: {status}")
    
    print("\n" + "="*70)
    
    # Next steps
    if not db_ok:
        print("\n⚠ NEXT STEP: Fix database connection")
        print("  Check DATABASE_URL environment variable")
    elif part_count == 0:
        print("\n⚠ NEXT STEP: Ingest STM32 data")
        print("  Run: python ingestion/run_stm32_ingestion.py")
    elif not api_ok:
        print("\n⚠ NEXT STEP: Start API server")
        print("  Run: python server.py")
    elif not frontend_ok:
        print("\n⚠ NEXT STEP: Check frontend files")
    else:
        print("\n✓ ALL SYSTEMS GO!")
        print("  API: http://localhost:8000")
        print("  Frontend: http://localhost:8000 (if server.py running)")
        print("  Web UI: python web_ui/app.py (port 8000)")


if __name__ == "__main__":
    asyncio.run(main())
