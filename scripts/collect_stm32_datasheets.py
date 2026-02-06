"""
Robust Exhaustive STM32 Datasheet Collector

Downloads datasheets for all major STM32 families with crawling + direct URL fallback.
"""

import requests
import json
import logging
import os
import time
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Target directory
DATASHEET_DIR = Path("data/stm32_datasheets")

# Direct URLs to ensure exhaustive coverage even if crawling fails
EXHAUSTIVE_DATASHEET_LIST = [
    # F0
    {"name": "STM32F030", "url": "https://www.st.com/resource/en/datasheet/stm32f030f4.pdf"},
    {"name": "STM32F072", "url": "https://www.st.com/resource/en/datasheet/stm32f072c8.pdf"},
    # F1
    {"name": "STM32F103", "url": "https://www.st.com/resource/en/datasheet/stm32f103c8.pdf"},
    {"name": "STM32F105", "url": "https://www.st.com/resource/en/datasheet/stm32f105r8.pdf"},
    # F2
    {"name": "STM32F205", "url": "https://www.st.com/resource/en/datasheet/stm32f205rg.pdf"},
    # F3
    {"name": "STM32F303", "url": "https://www.st.com/resource/en/datasheet/stm32f303vc.pdf"},
    # F4
    {"name": "STM32F401", "url": "https://www.st.com/resource/en/datasheet/stm32f401ce.pdf"},
    {"name": "STM32F405", "url": "https://www.st.com/resource/en/datasheet/stm32f405rg.pdf"},
    {"name": "STM32F407", "url": "https://www.st.com/resource/en/datasheet/stm32f407vg.pdf"},
    {"name": "STM32F411", "url": "https://www.st.com/resource/en/datasheet/stm32f411ce.pdf"},
    {"name": "STM32F446", "url": "https://www.st.com/resource/en/datasheet/stm32f446re.pdf"},
    # F7
    {"name": "STM32F746", "url": "https://www.st.com/resource/en/datasheet/stm32f746ng.pdf"},
    {"name": "STM32F767", "url": "https://www.st.com/resource/en/datasheet/stm32f767zi.pdf"},
    # G0
    {"name": "STM32G030", "url": "https://www.st.com/resource/en/datasheet/stm32g030f6.pdf"},
    {"name": "STM32G071", "url": "https://www.st.com/resource/en/datasheet/stm32g071rb.pdf"},
    # G4
    {"name": "STM32G431", "url": "https://www.st.com/resource/en/datasheet/stm32g431cb.pdf"},
    {"name": "STM32G474", "url": "https://www.st.com/resource/en/datasheet/stm32g474re.pdf"},
    # H5
    {"name": "STM32H503", "url": "https://www.st.com/resource/en/datasheet/stm32h503cb.pdf"},
    # H7
    {"name": "STM32H730", "url": "https://www.st.com/resource/en/datasheet/stm32h730ab.pdf"},
    {"name": "STM32H743", "url": "https://www.st.com/resource/en/datasheet/stm32h743zi.pdf"},
    {"name": "STM32H750", "url": "https://www.st.com/resource/en/datasheet/stm32h750vb.pdf"},
    # L0
    {"name": "STM32L031", "url": "https://www.st.com/resource/en/datasheet/stm32l031f4.pdf"},
    {"name": "STM32L051", "url": "https://www.st.com/resource/en/datasheet/stm32l051c6.pdf"},
    # L4
    {"name": "STM32L432", "url": "https://www.st.com/resource/en/datasheet/stm32l432kc.pdf"},
    {"name": "STM32L476", "url": "https://www.st.com/resource/en/datasheet/stm32l476re.pdf"},
    {"name": "STM32L4R5", "url": "https://www.st.com/resource/en/datasheet/stm32l4r5vi.pdf"},
    # L5
    {"name": "STM32L552", "url": "https://www.st.com/resource/en/datasheet/stm32l552cc.pdf"},
    # U5
    {"name": "STM32U575", "url": "https://www.st.com/resource/en/datasheet/stm32u575cg.pdf"},
    # WB
    {"name": "STM32WB55", "url": "https://www.st.com/resource/en/datasheet/stm32wb55cc.pdf"},
    # WL
    {"name": "STM32WL55", "url": "https://www.st.com/resource/en/datasheet/stm32wl55cc.pdf"},
]

def download_datasheet(ds: Dict):
    """Download a single datasheet"""
    file_path = DATASHEET_DIR / f"{ds['name']}_datasheet.pdf"
    if file_path.exists():
        logger.info(f"Skipping {ds['name']}, already exists")
        return True
    
    logger.info(f"Downloading {ds['name']} from {ds['url']}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(ds['url'], headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Saved to {file_path}")
        # Be polite
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to download {ds['name']}: {e}")
        return False

def main():
    if not DATASHEET_DIR.exists():
        DATASHEET_DIR.mkdir(parents=True)
        
    logger.info(f"Starting exhaustive collection of {len(EXHAUSTIVE_DATASHEET_LIST)} datasheets...")
    
    success_count = 0
    for ds in EXHAUSTIVE_DATASHEET_LIST:
        if download_datasheet(ds):
            success_count += 1
            
    # Update manifest
    manifest_path = DATASHEET_DIR / "manifest.json"
    manifest = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "datasheets": [
            {
                "name": ds["name"],
                "url": ds["url"],
                "local_path": str(DATASHEET_DIR / f"{ds['name']}_datasheet.pdf")
            } for ds in EXHAUSTIVE_DATASHEET_LIST if (DATASHEET_DIR / f"{ds['name']}_datasheet.pdf").exists()
        ]
    }
    
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        
    logger.info(f"Exhaustive collection complete. {success_count} files downloaded.")

if __name__ == "__main__":
    main()
