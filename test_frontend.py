
import urllib.request
import sys

try:
    print("Fetching http://localhost:8000/ ...")
    with urllib.request.urlopen("http://localhost:8000/") as response:
        content = response.read().decode('utf-8')
        print(f"Status: {response.status}")
        print(f"Content length: {len(content)}")
        if "<!DOCTYPE html>" in content or "<html" in content:
            print("Frontend HTML detected.")
        else:
            print("Frontend HTML NOT detected.")
        print("First 100 bytes:")
        print(content[:100])
except Exception as e:
    print(f"Failed to fetch frontend: {e}")
    sys.exit(1)
