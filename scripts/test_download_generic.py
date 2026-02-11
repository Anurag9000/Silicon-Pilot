
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.downloader import DatasheetDownloader
import logging

logging.basicConfig(level=logging.INFO)

def test():
    dl = DatasheetDownloader(download_dir="test_downloads")
    # Generic URL
    url = "https://www.google.com/robots.txt"
    print(f"Attempting to download {url}...")
    path = dl.download(url, "robots.txt")
    
    if path and os.path.exists(path):
        print(f"SUCCESS: {path} (Size: {os.path.getsize(path)} bytes)")
        with open(path, 'r') as f:
            print(f"Content head: {f.read(50)}...")
    else:
        print("FAILURE: Download returned None or file missing.")

if __name__ == "__main__":
    test()
