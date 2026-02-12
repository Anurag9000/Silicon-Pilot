
import sys
import os
from fastapi.testclient import TestClient

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from server import app
    print("SUCCESS: Imported app from server.py")
except ImportError as e:
    print(f"FAILURE: Could not import app from server.py: {e}")
    sys.exit(1)
except Exception as e:
    print(f"FAILURE: Error during import: {e}")
    sys.exit(1)

client = TestClient(app)

def test_routes():
    routes = [route.path for route in app.routes]
    expected_routes = [
        "/",
        "/api/templates",
        "/api/parse-intent",
        "/api/build-architecture",
        "/api/export",
        "/downloads/{filename}",
        "/api/search",
        "/api/parts/{part_id}/pins",
        "/recommend"
    ]
    
    missing = []
    for expected in expected_routes:
        if expected not in routes:
            missing.append(expected)
    
    if missing:
        print(f"FAILURE: Missing routes: {missing}")
        # Print all routes for debugging
        # print("Available routes:", routes)
        sys.exit(1)
    else:
        print("SUCCESS: All expected unification routes are present.")

if __name__ == "__main__":
    test_routes()
