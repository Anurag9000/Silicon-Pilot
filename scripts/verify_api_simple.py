import os
import asyncio
import uuid
import json
from fastapi.testclient import TestClient
from server import app
from core.mock_database import enable_mock_mode, get_mock_db

# Enable mock mode
enable_mock_mode()

def verify_api_simple():
    print("Phase 3: Simplified API Integration Verification")
    
    # Manually trigger startup
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
    print("✓ Health check successful.")

    # 2. Test Part Details directly
    print("Testing GET /parts/{mpn}...")
    db = get_mock_db()
    part = asyncio.run(db.fetchrow("SELECT id, mpn FROM parts LIMIT 1"))
    if part:
        mpn = part['mpn']
        response = client.get(f"/parts/{mpn}")
        assert response.status_code == 200
        print(f"✓ Part details for {mpn} retrieved.")
    
    print("✓ Simplified API Integration verification complete.")

if __name__ == "__main__":
    verify_api_simple()
