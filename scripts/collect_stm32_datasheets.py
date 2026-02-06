"""
STM32 Datasheet Collector

Downloads official datasheets for all STM32 microcontrollers from ST's website.
"""

import logging
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


class STM32DatasheetCollector:
    """Collect STM32 datasheets from ST's official website"""
    
    def __init__(self, output_dir: str = "data/stm32_datasheets"):
        """
        Initialize collector.
        
        Args:
            output_dir: Directory to save datasheets
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        
        # ST's product selector pages
        self.base_urls = {
            'STM32F0': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f0-series.html',
            'STM32F1': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f1-series.html',
            'STM32F2': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f2-series.html',
            'STM32F3': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f3-series.html',
            'STM32F4': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html',
            'STM32F7': 'https://www.st.com/en/microcontrollers-microprocessors/stm32f7-series.html',
            'STM32G0': 'https://www.st.com/en/microcontrollers-microprocessors/stm32g0-series.html',
            'STM32G4': 'https://www.st.com/en/microcontrollers-microprocessors/stm32g4-series.html',
            'STM32H7': 'https://www.st.com/en/microcontrollers-microprocessors/stm32h7-series.html',
            'STM32L0': 'https://www.st.com/en/microcontrollers-microprocessors/stm32l0-series.html',
            'STM32L1': 'https://www.st.com/en/microcontrollers-microprocessors/stm32l1-series.html',
            'STM32L4': 'https://www.st.com/en/microcontrollers-microprocessors/stm32l4-series.html',
            'STM32L5': 'https://www.st.com/en/microcontrollers-microprocessors/stm32l5-series.html',
            'STM32U5': 'https://www.st.com/en/microcontrollers-microprocessors/stm32u5-series.html',
            'STM32WB': 'https://www.st.com/en/microcontrollers-microprocessors/stm32wb-series.html',
            'STM32WL': 'https://www.st.com/en/microcontrollers-microprocessors/stm32wl-series.html',
        }
        
        # Known direct datasheet URLs for popular parts
        self.known_datasheets = {
            'STM32F405': 'https://www.st.com/resource/en/datasheet/stm32f405rg.pdf',
            'STM32F407': 'https://www.st.com/resource/en/datasheet/stm32f407vg.pdf',
            'STM32F429': 'https://www.st.com/resource/en/datasheet/stm32f429zi.pdf',
            'STM32F746': 'https://www.st.com/resource/en/datasheet/stm32f746ng.pdf',
            'STM32F767': 'https://www.st.com/resource/en/datasheet/stm32f767zi.pdf',
            'STM32H743': 'https://www.st.com/resource/en/datasheet/stm32h743zi.pdf',
            'STM32H750': 'https://www.st.com/resource/en/datasheet/stm32h750vb.pdf',
            'STM32L476': 'https://www.st.com/resource/en/datasheet/stm32l476rg.pdf',
            'STM32L4R5': 'https://www.st.com/resource/en/datasheet/stm32l4r5zi.pdf',
            'STM32G474': 'https://www.st.com/resource/en/datasheet/stm32g474cb.pdf',
            'STM32WB55': 'https://www.st.com/resource/en/datasheet/stm32wb55cc.pdf',
            'STM32F103': 'https://www.st.com/resource/en/datasheet/stm32f103c8.pdf',
            'STM32F072': 'https://www.st.com/resource/en/datasheet/stm32f072c8.pdf',
            'STM32F303': 'https://www.st.com/resource/en/datasheet/stm32f303cc.pdf',
            'STM32L432': 'https://www.st.com/resource/en/datasheet/stm32l432kc.pdf',
        }
    
    def download_file(self, url: str, filename: str) -> bool:
        """
        Download a file from URL.
        
        Args:
            url: File URL
            filename: Local filename to save
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Downloading: {url}")
            
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            filepath = self.output_dir / filename
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Saved: {filepath} ({filepath.stat().st_size} bytes)")
            return True
        
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def collect_known_datasheets(self) -> List[Dict[str, str]]:
        """
        Download known datasheets.
        
        Returns:
            List of downloaded datasheet info
        """
        logger.info("Downloading known STM32 datasheets")
        
        results = []
        
        for part_family, url in self.known_datasheets.items():
            # Rate limiting
            time.sleep(2)
            
            filename = f"{part_family}_datasheet.pdf"
            
            if self.download_file(url, filename):
                results.append({
                    'part_family': part_family,
                    'url': url,
                    'filename': filename,
                    'filepath': str(self.output_dir / filename),
                })
        
        return results
    
    def save_manifest(self, datasheets: List[Dict[str, str]]):
        """
        Save manifest of downloaded datasheets.
        
        Args:
            datasheets: List of datasheet info
        """
        manifest_path = self.output_dir / 'manifest.json'
        
        manifest = {
            'total_datasheets': len(datasheets),
            'datasheets': datasheets,
            'collected_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"Saved manifest: {manifest_path}")
    
    def collect_all(self) -> List[Dict[str, str]]:
        """
        Collect all STM32 datasheets.
        
        Returns:
            List of downloaded datasheet info
        """
        logger.info("Starting STM32 datasheet collection")
        
        # For now, collect known datasheets
        # In production, would crawl ST's product pages
        datasheets = self.collect_known_datasheets()
        
        # Save manifest
        self.save_manifest(datasheets)
        
        logger.info(f"Collection complete: {len(datasheets)} datasheets")
        
        return datasheets


def main():
    """Main entry point"""
    collector = STM32DatasheetCollector()
    datasheets = collector.collect_all()
    
    print(f"\n✅ Downloaded {len(datasheets)} STM32 datasheets")
    print(f"📁 Saved to: {collector.output_dir}")
    print(f"📋 Manifest: {collector.output_dir / 'manifest.json'}")


if __name__ == '__main__':
    main()
