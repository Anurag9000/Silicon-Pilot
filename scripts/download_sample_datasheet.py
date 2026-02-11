
import os
import requests
from pathlib import Path

DATASHEET_URL = "https://www.st.com/resource/en/datasheet/stm32f405rg.pdf"
OUTPUT_DIR = Path("d:/Done,Toreview/HardwareGenius/datasheets")
OUTPUT_FILE = OUTPUT_DIR / "stm32f405.pdf"

def download_datasheet():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading STM32F405 datasheet from {DATASHEET_URL}...")
    try:
        response = requests.get(DATASHEET_URL, stream=True)
        response.raise_for_status()
        
        with open(OUTPUT_FILE, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Download complete: {OUTPUT_FILE}")
        print(f"Size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")
        
    except Exception as e:
        print(f"Error downloading datasheet: {e}")

if __name__ == "__main__":
    download_datasheet()
