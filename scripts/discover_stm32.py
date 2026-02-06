"""
STM32 Discovery Script

Fetches the complete product list from ST's product grid JSON API.
"""

import requests
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Likely product grid URL for STM32
GRID_URL = "https://www.st.com/content/st_com/en/products/microcontrollers-microprocessors/stm32-32-bit-arm-cortex-mcus.product-grid.json"

def discover_products():
    """Fetch product list from ST"""
    logger.info(f"Fetching product grid from {GRID_URL}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(GRID_URL, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Save raw data for inspection
        with open("data/stm32_product_grid.json", "w") as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Successfully saved product grid to data/stm32_product_grid.json")
        
        # Extract products (structure depends on ST's API)
        # Usually it's in data['products'] or data['rows']
        products = data.get('products', [])
        logger.info(f"Found {len(products)} products in grid")
        
        return products
    except Exception as e:
        logger.error(f"Failed to fetch product grid: {e}")
        return []

if __name__ == "__main__":
    if not os.path.exists("data"):
        os.makedirs("data")
    discover_products()
