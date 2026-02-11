
import requests
import json

URL = "http://localhost:8000/api/search"

def test_search():
    # Test 1: Search by MPN
    print("Test 1: Search 'F405'...")
    payload = {"query": "F405", "limit": 5}
    try:
        res = requests.post(URL, json=payload)
        res.raise_for_status()
        data = res.json()
        print(f"  Found {data['count']} parts.")
        if data['count'] > 0:
            print(f"  Sample: {data['results'][0]['mpn']} - ${data['results'][0]['cost_usd']}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Filter by Flash > 512KB
    print("\nTest 2: Search Flash > 512KB...")
    payload = {"flash_min_kb": 512, "limit": 5}
    try:
        res = requests.post(URL, json=payload)
        res.raise_for_status()
        data = res.json()
        print(f"  Found {data['count']} parts.")
        if data['count'] > 0:
             print(f"  Sample: {data['results'][0]['mpn']} - Flash: {data['results'][0]['flash_kb']}KB")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    test_search()
