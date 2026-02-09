"""
Comprehensive STM32 Documentation Downloader

Downloads ALL STM32 family documentation from ST.com:
- Datasheets (DS)
- Reference Manuals (RM)
- Programming Manuals (PM)
- Errata Sheets (ES)
- Application Notes (AN)

Covers ALL STM32 families: F0, F1, F2, F3, F4, F7, G0, G4, H7, L0, L1, L4, L5, U5, WB, WL, C0
"""

import requests
from bs4 import BeautifulSoup
import time
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re
from typing import List, Dict, Set
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Base configuration
BASE_URL = "https://www.st.com"
OUTPUT_DIR = Path("data/stm32_documentation")
DELAY_BETWEEN_REQUESTS = 2.0  # Respectful delay
MAX_RETRIES = 3

# All STM32 families with their product page URLs
STM32_FAMILIES = {
    # Mainstream (Cortex-M0/M0+/M3/M4/M7)
    "STM32F0": "https://www.st.com/en/microcontrollers-microprocessors/stm32f0-series.html",
    "STM32F1": "https://www.st.com/en/microcontrollers-microprocessors/stm32f1-series.html",
    "STM32F2": "https://www.st.com/en/microcontrollers-microprocessors/stm32f2-series.html",
    "STM32F3": "https://www.st.com/en/microcontrollers-microprocessors/stm32f3-series.html",
    "STM32F4": "https://www.st.com/en/microcontrollers-microprocessors/stm32f4-series.html",
    "STM32F7": "https://www.st.com/en/microcontrollers-microprocessors/stm32f7-series.html",
    
    # High-performance (Cortex-M7/M4)
    "STM32H7": "https://www.st.com/en/microcontrollers-microprocessors/stm32h7-series.html",
    "STM32H5": "https://www.st.com/en/microcontrollers-microprocessors/stm32h5-series.html",
    
    # Ultra-low-power
    "STM32L0": "https://www.st.com/en/microcontrollers-microprocessors/stm32l0-series.html",
    "STM32L1": "https://www.st.com/en/microcontrollers-microprocessors/stm32l1-series.html",
    "STM32L4": "https://www.st.com/en/microcontrollers-microprocessors/stm32l4-series.html",
    "STM32L4+": "https://www.st.com/en/microcontrollers-microprocessors/stm32l4-plus-series.html",
    "STM32L5": "https://www.st.com/en/microcontrollers-microprocessors/stm32l5-series.html",
    "STM32U5": "https://www.st.com/en/microcontrollers-microprocessors/stm32u5-series.html",
    
    # Mainstream value line
    "STM32G0": "https://www.st.com/en/microcontrollers-microprocessors/stm32g0-series.html",
    "STM32G4": "https://www.st.com/en/microcontrollers-microprocessors/stm32g4-series.html",
    "STM32C0": "https://www.st.com/en/microcontrollers-microprocessors/stm32c0-series.html",
    
    # Wireless
    "STM32WB": "https://www.st.com/en/microcontrollers-microprocessors/stm32wb-series.html",
    "STM32WBA": "https://www.st.com/en/microcontrollers-microprocessors/stm32wba-series.html",
    "STM32WL": "https://www.st.com/en/microcontrollers-microprocessors/stm32wl-series.html",
    
    # Mixed-signal
    "STM32G4": "https://www.st.com/en/microcontrollers-microprocessors/stm32g4-series.html",
}

# Document types to download
DOCUMENT_TYPES = {
    "datasheet": ["DS", "datasheet"],
    "reference_manual": ["RM", "reference manual"],
    "programming_manual": ["PM", "programming manual"],
    "errata": ["ES", "errata"],
    "application_note": ["AN", "application note"],
}

class STM32DocumentDownloader:
    def __init__(self, output_dir: Path = OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded_urls: Set[str] = set()
        self.download_log = []
        
    def download_file(self, url: str, output_path: Path, retries: int = MAX_RETRIES) -> bool:
        """Download a file with retry logic"""
        if url in self.downloaded_urls:
            logger.info(f"Already downloaded: {url}")
            return True
            
        for attempt in range(retries):
            try:
                logger.info(f"Downloading: {url} (attempt {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=30, stream=True)
                response.raise_for_status()
                
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                self.downloaded_urls.add(url)
                logger.info(f"✓ Downloaded: {output_path.name}")
                return True
                
            except Exception as e:
                logger.error(f"Download failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(DELAY_BETWEEN_REQUESTS * 2)
                    
        return False
    
    def fetch_page(self, url: str, retries: int = MAX_RETRIES) -> str:
        """Fetch HTML page with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                time.sleep(DELAY_BETWEEN_REQUESTS)
                return response.text
            except Exception as e:
                logger.error(f"Page fetch failed (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(DELAY_BETWEEN_REQUESTS * 2)
        return ""
    
    def extract_product_links(self, family_url: str) -> List[str]:
        """Extract all product page links from a family page"""
        logger.info(f"Extracting products from: {family_url}")
        html = self.fetch_page(family_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        product_links = []
        
        # Look for product links (ST.com uses various patterns)
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Match STM32 product pages
            if '/en/product/' in href or '/content/st_com/en/products/' in href:
                full_url = urljoin(BASE_URL, href)
                if full_url not in product_links:
                    product_links.append(full_url)
        
        logger.info(f"Found {len(product_links)} product links")
        return product_links
    
    def extract_documentation_links(self, product_url: str) -> Dict[str, List[str]]:
        """Extract all documentation download links from a product page"""
        logger.info(f"Extracting documentation from: {product_url}")
        html = self.fetch_page(product_url)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        docs = {doc_type: [] for doc_type in DOCUMENT_TYPES.keys()}
        
        # Find all PDF links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '.pdf' in href.lower():
                full_url = urljoin(BASE_URL, href)
                text = link.get_text().lower()
                
                # Categorize by document type
                for doc_type, keywords in DOCUMENT_TYPES.items():
                    if any(keyword.lower() in text or keyword.lower() in href.lower() for keyword in keywords):
                        if full_url not in docs[doc_type]:
                            docs[doc_type].append(full_url)
        
        total_docs = sum(len(links) for links in docs.values())
        logger.info(f"Found {total_docs} documentation files")
        return docs
    
    def download_family_documentation(self, family_name: str, family_url: str):
        """Download all documentation for a specific STM32 family"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing family: {family_name}")
        logger.info(f"{'='*60}")
        
        family_dir = self.output_dir / family_name
        family_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract product links
        product_links = self.extract_product_links(family_url)
        
        if not product_links:
            logger.warning(f"No products found for {family_name}, trying direct documentation...")
            # Try to get documentation directly from family page
            docs = self.extract_documentation_links(family_url)
            self.download_documents(docs, family_dir / "family_docs")
            return
        
        # Process each product
        for idx, product_url in enumerate(product_links, 1):
            logger.info(f"\n[{idx}/{len(product_links)}] Processing: {product_url}")
            
            # Extract product name from URL
            product_name = urlparse(product_url).path.split('/')[-1].replace('.html', '')
            product_dir = family_dir / product_name
            
            # Get documentation links
            docs = self.extract_documentation_links(product_url)
            
            # Download all documents
            self.download_documents(docs, product_dir)
            
            # Log progress
            self.download_log.append({
                'family': family_name,
                'product': product_name,
                'url': product_url,
                'docs_found': sum(len(links) for links in docs.values())
            })
    
    def download_documents(self, docs: Dict[str, List[str]], base_dir: Path):
        """Download categorized documents"""
        for doc_type, urls in docs.items():
            if not urls:
                continue
                
            doc_type_dir = base_dir / doc_type
            
            for url in urls:
                # Extract filename from URL
                filename = os.path.basename(urlparse(url).path)
                if not filename.endswith('.pdf'):
                    filename += '.pdf'
                
                output_path = doc_type_dir / filename
                
                if output_path.exists():
                    logger.info(f"Already exists: {filename}")
                    continue
                
                self.download_file(url, output_path)
                time.sleep(DELAY_BETWEEN_REQUESTS)
    
    def download_all_families(self):
        """Download documentation for all STM32 families"""
        logger.info(f"\n{'#'*60}")
        logger.info(f"Starting comprehensive STM32 documentation download")
        logger.info(f"Total families: {len(STM32_FAMILIES)}")
        logger.info(f"Output directory: {self.output_dir.absolute()}")
        logger.info(f"{'#'*60}\n")
        
        for idx, (family_name, family_url) in enumerate(STM32_FAMILIES.items(), 1):
            logger.info(f"\n>>> Family {idx}/{len(STM32_FAMILIES)}: {family_name}")
            try:
                self.download_family_documentation(family_name, family_url)
            except Exception as e:
                logger.error(f"Failed to process {family_name}: {e}")
                continue
        
        # Save download log
        log_path = self.output_dir / "download_log.json"
        with open(log_path, 'w') as f:
            json.dump(self.download_log, f, indent=2)
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"Download complete!")
        logger.info(f"Total files downloaded: {len(self.downloaded_urls)}")
        logger.info(f"Log saved to: {log_path}")
        logger.info(f"{'#'*60}")


def main():
    downloader = STM32DocumentDownloader()
    downloader.download_all_families()


if __name__ == "__main__":
    main()
