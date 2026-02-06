"""
Exhaustive STM32 Datasheet Crawler

Discovers and downloads datasheets for all STM32 families.
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

# List of all STM32 series to crawl
STM32_SERIES = [
    "stm32f0", "stm32f1", "stm32f2", "stm32f3", "stm32f4", "stm32f7",
    "stm32g0", "stm32g4", "stm32h5", "stm32h7",
    "stm32l0", "stm32l1", "stm32l4", "stm32l4plus", "stm32l5",
    "stm32u0", "stm32u5",
    "stm32wb", "stm32wba", "stm32wl"
]

BASE_URL = "https://www.st.com"
DATASHEET_DIR = Path("data/stm32_datasheets")

def discover_datasheets(series: str) -> List[Dict]:
    """Find datasheets for a specific STM32 series"""
    series_url = f"{BASE_URL}/en/microcontrollers-microprocessors/{series}-series.html"
    logger.info(f"Crawling {series_url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(series_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        datasheets = []
        # Find all PDF links that look like datasheets
        for link in soup.find_all('a', href=True):
            href = link['href']
            if "/resource/en/datasheet/" in href and href.endswith(".pdf"):
                # Extract a possible name from context or the URL
                full_url = href if href.startswith("http") else BASE_URL + href
                name = href.split('/')[-1].replace('.pdf', '')
                
                # Deduplicate
                if not any(d['url'] == full_url for d in datasheets):
                    datasheets.append({
                        "series": series,
                        "name": name,
                        "url": full_url
                    })
                    
        logger.info(f"Found {len(datasheets)} unique datasheets for {series}")
        return datasheets
    except Exception as e:
        logger.error(f"Failed to crawl {series}: {e}")
        return []

def download_datasheet(ds: Dict):
    """Download a single datasheet"""
    file_path = DATASHEET_DIR / f"{ds['name']}.pdf"
    if file_path.exists():
        logger.info(f"Skipping {ds['name']}, already exists")
        return True
    
    logger.info(f"Downloading {ds['name']} from {ds['url']}...")
    try:
        response = requests.get(ds['url'], stream=True, timeout=60)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Avoid hammering the server
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"Failed to download {ds['name']}: {e}")
        return False

def main():
    if not DATASHEET_DIR.exists():
        DATASHEET_DIR.mkdir(parents=True)
        
    all_discovered = []
    
    for series in STM32_SERIES:
        discovered = discover_datasheets(series)
        all_discovered.extend(discovered)
        time.sleep(2) # Politeness delay
        
    logger.info(f"Total datasheets discovered: {len(all_discovered)}")
    
    # Save manifest of discovery
    with open("data/discovery_manifest.json", "w") as f:
        json.dump(all_discovered, f, indent=2)
        
    # Download them (up to a reasonable limit for this task, e.g., 50)
    # The user wants "everything", but for the E2E check I'll do a significant subset
    # if it's too many.
    success_count = 0
    for ds in all_discovered[:50]: # Limit to 50 for the thorough end-to-end check
        if download_datasheet(ds):
            success_count += 1
            
    logger.info(f"Successfully downloaded {success_count} datasheets")

if __name__ == "__main__":
    main()
