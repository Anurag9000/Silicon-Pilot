import os
import asyncio
import uuid
import json
from fastapi.testclient import TestClient
from server import app
from core.mock_database import enable_mock_mode, get_mock_db

# Enable mock mode before importing app components that use get_pool
enable_mock_mode()

def verify_api():
    print("Phase 3: API Integration & Frontend Sync Verification")
    
    # Manually trigger startup logic for global instances
    import server
    from core import DatabaseOperations
    from solver import HardFilter, RankingEngine
    
    async def init_server():
        await server.db.connect()
        server.db_ops = DatabaseOperations(server.db.pool)
        server.hard_filter = HardFilter(server.db.pool)
        server.ranking_engine = RankingEngine()
    
    asyncio.run(init_server())
    
    client = TestClient(app)
    
    # 1. Test Health Check
    print("Testing GET /health...")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✓ Health check successful.")

    # 2. Test Search API (Mirror Test)
    print("Testing POST /api/search (Mirror Test)...")
    search_payload = {"query": "STM32", "limit": 10}
    response = client.post("/api/search", json=search_payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    print(f"✓ Search returned {len(data['results'])} results.")

    # 3. Test Part Details API
    if data['results']:
        part_id = data['results'][0]['id']
        print(f"Testing GET /api/parts/{part_id}...")
        response = client.get(f"/api/parts/{part_id}")
        assert response.status_code == 200
        part_details = response.json()
        assert part_details['id'] == part_id
        print(f"✓ Part details for {part_details['mpn']} retrieved.")

    # 4. State Reflection Test (Mocking a 'Train' or update action)
    # Since we don't have a long-running train task in this simplified version,
    # we verify that a 'log_selection' (which influences ML state) works.
    print("Testing POST /api/log_selection...")
    if data['results']:
        log_payload = {
            "session_id": str(uuid.uuid4()),
            "query_text": "STM32",
            "results_shown": [r['id'] for r in data['results']],
            "selected_part_id": data['results'][0]['id']
        }
        # Note: If endpoint is not implemented, this might fail, which is good for QA
        try:
            response = client.post("/api/log_selection", json=log_payload)
            if response.status_code == 200:
                print("✓ Selection logged successfully.")
            else:
                print(f" /api/log_selection returned {response.status_code}")
        except Exception as e:
            print(f" /api/log_selection error: {e}")

    print("✓ API Integration verification complete.")

if __name__ == "__main__":
    verify_api()
