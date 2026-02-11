
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.downloader import DatasheetDownloader
import logging

logging.basicConfig(level=logging.INFO)

def test():
    dl = DatasheetDownloader(download_dir="test_downloads")
    # Known valid URL
    url = "https://www.st.com/resource/en/errata_sheet/es0182.pdf"
    print(f"Attempting to download {url}...")
    path = dl.download(url, "es0182.pdf")
    
    if path and os.path.exists(path):
        print(f"SUCCESS: {path} (Size: {os.path.getsize(path)} bytes)")
    else:
        print("FAILURE: Download returned None or file missing.")

if __name__ == "__main__":
    test()
