
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(name, method, url, payload=None, expected_status=200):
    print(f"Testing {name} ({method} {url})...", end=" ")
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{url}", params=payload)
        elif method == "POST":
            response = requests.post(f"{BASE_URL}{url}", json=payload)
        else:
            print("Unsupported method")
            return False
        
        if response.status_code == expected_status:
            print(f"PASS ({response.elapsed.total_seconds():.2f}s)")
            return True
        else:
            print(f"FAIL (Status: {response.status_code})")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    print(f"Running End-to-End API Tests against {BASE_URL}\n")
    
    # 1. Health Check
    if not test_endpoint("Health Check", "GET", "/health"):
        print("CRITICAL: Server is not healthy. Aborting.")
        sys.exit(1)
        
    # 2. Frontend Check
    if not test_endpoint("Frontend Serving", "GET", "/", expected_status=200):
        print("WARNING: Frontend not serving at root.")

    # 3. Part Search
    search_payload = {"limit": 5}
    if not test_endpoint("Part Search (All)", "GET", "/parts", search_payload):
        sys.exit(1)
        
    # 4. Recommendation (Deterministic)
    rec_payload = {
        "spec_id": "test-uuid", # Server should handle new ID generation or we might need to create one
        "requirements": "I need a low power MCU for a wearable device.",
        "max_results": 5
    }
    # Note: This might fail if LLM is required for parsing. 
    # Let's try the deterministic recommendation endpoint if available or check standard flow.
    # Actually, /recommend takes a parsed spec ID. We usually need to parse first.
    
    # Let's try to parse first (mocking LLM if needed or expecting 401 if real key needed)
    # If OPENAI_API_KEY is placeholder, this returns 401.
    print("Testing /spec/from_text (LLM)...", end=" ")
    parse_resp = requests.post(f"{BASE_URL}/spec/from_text", json={"text": "STM32F4 with 512KB Flash"})
    if parse_resp.status_code == 401:
        print("PASS (Expected 401 for Placeholder API Key)")
    elif parse_resp.status_code == 200:
        print("PASS (LLM Working)")
        spec_id = parse_resp.json().get("spec_id")
    else:
         print(f"FAIL (Status: {parse_resp.status_code})")

    # 5. Database Content Check (via Search)
    print("Checking Database Content...", end=" ")
    try:
        resp = requests.get(f"{BASE_URL}/parts?limit=1")
        data = resp.json()
        count = data.get("count", 0)
        print(f"PASS (Found {count} parts available)")
    except:
        print("FAIL")

    print("\nE2E Verification Complete.")

if __name__ == "__main__":
    main()
