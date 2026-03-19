import os
import asyncio
import uuid
import sys
import numpy as np
from ml.ranker import MLRanker, RankingFeatures
from core.mock_database import get_mock_db, MockPool

# Patch MLRanker to use MockPool/MockDatabase
class PatchedMLRanker(MLRanker):
    async def extract_features(self, part_id, query_text=""):
        db = get_mock_db()
        # MCU specs query adapted for SQLite
        part = await db.fetchrow("""
            SELECT p.*, m.flash_kb, m.ram_kb, m.max_mhz,
                   m.uart_count, m.spi_count, m.i2c_count, m.can_count,
                   m.adc_channels as adc_count, m.cost_usd
            FROM parts p
            LEFT JOIN mcu_specs m ON p.id = m.part_id
            WHERE p.id = ?
        """, str(part_id))
        
        if not part:
            return None
        
        # Calculate peripheral count
        peripheral_count = sum([
            part.get('uart_count') or 0,
            part.get('spi_count') or 0,
            part.get('i2c_count') or 0,
            part.get('can_count') or 0,
            part.get('adc_count') or 0
        ])
        
        # Simple scores
        manufacturer_popularity = 0.8
        spec_completeness = 0.9
        query_match_score = 0.5
        if query_text.lower() in part['mpn'].lower():
            query_match_score = 1.0
            
        cost_score = 1.0 / (part.get('cost_usd') or 1.0)
        availability_score = 0.8
        
        return RankingFeatures(
            flash_kb=float(part.get('flash_kb') or 0),
            ram_kb=float(part.get('ram_kb') or 0),
            max_freq_mhz=float(part.get('max_mhz') or 0),
            peripheral_count=peripheral_count,
            manufacturer_popularity=manufacturer_popularity,
            spec_completeness=spec_completeness,
            query_match_score=query_match_score,
            cost_score=min(1.0, cost_score),
            availability_score=availability_score
        )

async def verify_ranker():
    print("Phase 2: ML Ranker Deep-Dive Verification")
    db = get_mock_db()
    
    # Get some real part IDs from mock DB
    parts = await db.fetch("SELECT id, mpn FROM parts LIMIT 5")
    part_ids = [p['id'] for p in parts]
    
    print(f"Ranking {len(part_ids)} parts for query 'STM32'...")
    
    ranker = PatchedMLRanker("mock_url")
    ranked_results = await ranker.rank_parts(part_ids, query_text="STM32")
    
    print(f"{'Part ID':<40} | {'Score':<10}")
    print("-" * 55)
    
    for part_id, score in ranked_results:
        # Get MPN for display
        mpn = next(p['mpn'] for p in parts if p['id'] == part_id)
        print(f"{mpn:<40} | {score:.2f}")
        
        # Output Validation: Ensure score is a valid float and not NaN
        assert isinstance(score, float)
        assert not np.isnan(score)
        
    print("✓ ML Ranker inference verification successful.")
    db.close()

if __name__ == "__main__":
    asyncio.run(verify_ranker())
