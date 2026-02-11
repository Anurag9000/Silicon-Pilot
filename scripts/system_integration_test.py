import requests
import sys

def test_integration():
    print("Testing System Integration...")
    
    # 1. Test Backend API
    try:
        print("\n[Backend] Checking connectivity...")
        r = requests.get("http://127.0.0.1:8000/docs", timeout=5)
        if r.status_code == 200:
            print("  ✓ Backend accessible (Docs UI)")
        else:
            print(f"  ✗ Backend returned status {r.status_code}")
    except Exception as e:
        print(f"  ✗ Backend connection failed: {e}")

    # 2. Test Frontend
    try:
        print("\n[Frontend] Checking connectivity...")
        r = requests.get("http://127.0.0.1:8001", timeout=5)
        if r.status_code == 200:
            print("  ✓ Frontend accessible")
        else:
            print(f"  ✗ Frontend returned status {r.status_code}")
    except Exception as e:
        print(f"  ✗ Frontend connection failed: {e}")

if __name__ == "__main__":
    test_integration()
