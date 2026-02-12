"""
ML Ranking Engine

Ranks component candidates based on multiple factors:
- Price (cost efficiency)
- Logistical Risk (stock levels, lead time)
- Technical Suitability (margin over specs)
- Documentation Quality (errata count, datasheet completeness)

Currently uses a weighted heuristic model, designed to be replaced by
a trained XGBoost/LightGBM model as user interaction data accumulates.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math

@dataclass
class Candidate:
    id: str  # UUID
    mpn: str
    manufacturer: str
    price_usd: float
    stock_qty: int
    specs: Dict[str, Any]
    score: float = 0.0
    rank_reasons: List[str] = None

class RankingEngine:
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        # Default weights for heuristic model
        self.weights = weights or {
            "price": 0.4,
            "availability": 0.3,
            "technical_margin": 0.2,
            "documentation": 0.1
        }
    
    def rank_candidates(self, candidates: List[Dict[str, Any]], 
                       requirements: Dict[str, Any]) -> List[Candidate]:
        """
        Rank a list of candidates against requirements.
        
        Args:
            candidates: List of dicts with 'id', 'mpn', 'cost_usd', 'stock', 'specs'
            requirements: Dict of required specs (e.g., {'min_flash_kb': 64})
            
        Returns:
            List of Candidate objects sorted by score (descending)
        """
        scored_candidates = []
        
        # Calculate statistics for normalization
        prices = [c.get('cost_usd', 0) or 0 for c in candidates if c.get('cost_usd')]
        max_price = max(prices) if prices else 1.0
        min_price = min(prices) if prices else 0.0
        
        stocks = [c.get('stock', 0) or 0 for c in candidates]
        max_stock = max(stocks) if stocks else 1
        
        for cand in candidates:
            score = 0.0
            reasons = []
            
            # --- 1. Price Score (Lower is better) ---
            price = cand.get('cost_usd', 0) or 0
            if price > 0:
                # Normalize: 1.0 for cheapest, ~0.0 for most expensive
                # Linear interpolation: (max - price) / (max - min)
                if max_price > min_price:
                    price_score = (max_price - price) / (max_price - min_price)
                else:
                    price_score = 1.0
                
                weighted_score = price_score * self.weights['price']
                score += weighted_score
                if price_score > 0.8:
                    reasons.append(f"Great Price (${price:.2f})")
            
            # --- 2. Availability Score (Higher is better) ---
            stock = cand.get('stock', 0) or 0
            # Log scale for stock (diminishing returns after 10k units)
            # stock_score = log10(stock) / 5 (assuming max useful is 100k)
            if stock > 0:
                stock_score = min(math.log10(stock) / 5.0, 1.0)
                weighted_score = stock_score * self.weights['availability']
                score += weighted_score
                if stock > 1000:
                    reasons.append("High Availability")
            
            # --- 3. Technical Margin (Bonus for exceeding specs) ---
            # Example: Requested 64KB Flash, Candidate has 128KB -> Bonus
            # But not too much (cost ineffective)
            tech_score = 0.0
            specs = cand.get('specs', {})
            req_flash = requirements.get('min_flash_kb')
            cand_flash = specs.get('flash_kb')
            
            if req_flash and cand_flash:
                ratio = cand_flash / req_flash
                if 1.0 <= ratio <= 2.0:
                    tech_score = 1.0 # Perfect sweet spot
                    reasons.append("Optimal Flash Size")
                elif ratio > 2.0:
                    tech_score = 0.7 # Overkill
                else:
                    tech_score = 0.0 # Should be filtered out, but just in case
            
            score += tech_score * self.weights['technical_margin']
            
            # --- 4. Documentation (Placeholder) ---
            # Assume 1.0 for now if datasheets exist
            doc_score = 1.0 
            score += doc_score * self.weights['documentation']
            
            scored_candidates.append(Candidate(
                id=cand.get('id'),
                mpn=cand.get('mpn'),
                manufacturer=cand.get('manufacturer', 'Unknown'),
                price_usd=price,
                stock_qty=stock,
                specs=specs,
                score=score * 100, # Scale to 0-100
                rank_reasons=reasons
            ))
            
        # Sort
        scored_candidates.sort(key=lambda x: x.score, reverse=True)
        return scored_candidates

