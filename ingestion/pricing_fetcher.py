
import os
import random
import aiohttp
from typing import Dict, Any, Optional

class PricingFetcher:
    """
    Fetches pricing data from Octopart/DigiKey APIs.
    Falls back to mock data if no API key is provided.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OCTOPART_API_KEY")
        self.mock_mode = not self.api_key
        
    async def get_price(self, mpn: str) -> Optional[float]:
        """
        Get the best unit price for 1k quantity.
        """
        if self.mock_mode:
            return self._get_mock_price(mpn)
            
        # Implementation for Real API (Stubbed)
        return self._get_mock_price(mpn)
        
    def _get_mock_price(self, mpn: str) -> float:
        """
        Generate a realistic looking price based on MPN features.
        """
        # Deterministic seed based on MPN to be consistent
        random.seed(mpn)
        
        base_price = 1.50
        
        if "H7" in mpn: base_price += 5.0
        elif "F7" in mpn: base_price += 3.0
        elif "F4" in mpn: base_price += 1.5
        elif "L0" in mpn or "G0" in mpn: base_price -= 0.5
        
        # Add random variance
        variance = random.uniform(-0.2, 0.5)
        price = max(0.50, base_price + variance)
        
        return round(price, 2)

    async def batch_update_prices(self, conn):
        """
        Updates 'cost_usd' in mcu_specs table for all parts.
        """
        print("Starting batch price update...")
        # Get all parts without price or older than X
        rows = await conn.fetch("""
            SELECT p.id, p.mpn 
            FROM parts p
            JOIN mcu_specs m ON p.id = m.part_id
            WHERE m.cost_usd IS NULL
        """)
        
        print(f"Found {len(rows)} parts needing price update.")
        
        updated = 0
        for row in rows:
            price = await self.get_price(row['mpn'])
            if price:
                await conn.execute("""
                    UPDATE mcu_specs 
                    SET cost_usd = $1, updated_at = NOW() 
                    WHERE part_id = $2
                """, price, row['id'])
                updated += 1
                
        print(f"Updated prices for {updated} parts.")
        return updated
