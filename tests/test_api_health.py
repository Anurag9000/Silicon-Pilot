
import asyncio
import aiohttp
import sys

BASE_URL = "http://localhost:8000"

async def test_health():
    async with aiohttp.ClientSession() as session:
        try:
            print(f"Checking {BASE_URL}/health...")
            async with session.get(f"{BASE_URL}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Health check PASSED: {data}")
                else:
                    print(f"Health check FAILED: {resp.status} {await resp.text()}")
                    return False

            print(f"\nChecking {BASE_URL}/search (POST)...")
            payload = {
                "query": "STM32F4",
                "category": "mcu",
                "limit": 5
            }
            # Note: The actual endpoint might be /api/v1/search or similar, need to check server.py routes
            # Based on previous context, it seems to be /search or /api/v1/search
            # Let's try /search first based on server.py viewing (it showed @app.post("/spec/from_text")...)
            # Wait, server.py had @app.post("/spec/from_text") and others. 
            # It didn't seemingly have a simple /search. It has /recommend.
            # Let's try /recommend if /search fails, or check server.py again.
            
            # Re-reading server.py snippet:
            # @app.post("/spec/from_text")
            # @app.post("/spec/answer")
            # @app.post("/recommend")
            
            # So let's test /recommend which seems to be the main one.
            # But /recommend needs a spec_id.
            
            # Let's try creating a spec first.
            print(f"\nTesting full flow: Parse -> Recommend")
            
            # 1. Parse
            parse_payload = {"text": "I need a low power MCU for a battery operated IoT device with BLE and ADC."}
            print(f"Sending to /spec/from_text: {parse_payload}")
            async with session.post(f"{BASE_URL}/spec/from_text", json=parse_payload) as resp:
                if resp.status != 200:
                   print(f"Parse FAILED: {resp.status} {await resp.text()}")
                   return False
                parse_data = await resp.json()
                spec_id = parse_data['spec_id']
                print(f"Parse PASSED. Spec ID: {spec_id}")
            
            # 2. Recommend
            rec_payload = {"spec_id": spec_id, "max_results": 5}
            print(f"Sending to /recommend: {rec_payload}")
            async with session.post(f"{BASE_URL}/recommend", json=rec_payload) as resp:
                if resp.status != 200:
                    print(f"Recommend FAILED: {resp.status} {await resp.text()}")
                    return False
                rec_data = await resp.json()
                print(f"Recommend PASSED. Candidates found: {len(rec_data.get('candidates', []))}")
                
            return True

        except Exception as e:
            print(f"Test FAILED with exception: {e}")
            return False

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_health())
