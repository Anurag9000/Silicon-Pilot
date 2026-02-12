"""
Heuristic Ranking Engine

Ranks component candidates based on multiple factors:
- Price (cost efficiency)
- Logistical Risk (stock levels, lead time)
- Technical Suitability (margin over specs)
- Documentation Quality (errata count, datasheet completeness)

Currently uses a weighted heuristic model, designed to be replaced by
a trained XGBoost/LightGBM model as user interaction data accumulates.
"""

from dataclasses import dataclass, field
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
    rank_reasons: List[str] = field(default_factory=list)

class HeuristicRankingEngine:
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
        
        for cand in candidates:
            score = 0.0
            reasons = []
            
            # --- 1. Price Score (Lower is better) ---
            price = cand.get('cost_usd', 0) or 0
            if price > 0:
                # Normalize: 1.0 for cheapest, ~0.0 for most expensive
                if max_price > min_price:
                    price_score = (max_price - price) / (max_price - min_price)
                else:
                    # If all prices are the same (range is 0), score is 1.0 (neutral/good)
                    price_score = 1.0
                
                weighted_score = price_score * self.weights['price']
                score += weighted_score
                if price_score > 0.8:
                    reasons.append(f"Great Price (${price:.2f})")
            else:
                 # No price data - neutral score (0.5 normalized)
                 score += 0.5 * self.weights['price']
            
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
            # Iterate over relevant numeric specs
            tech_scores = []
            specs = cand.get('specs', {})
            
            # Mapping of requirement keys to spec keys
            # requirement key -> spec key
            metrics = {
                'min_flash_kb': 'flash_kb',
                'min_sram_kb': 'sram_kb',
                'min_pin_count': 'pin_count',
                'min_max_mhz': 'max_mhz'
            }
            
            for req_key, spec_key in metrics.items():
                req_val = requirements.get(req_key)
                if not req_val:
                    continue
                    
                cand_val = specs.get(spec_key)
                if not cand_val:
                    continue
                
                ratio = cand_val / req_val
                if 1.0 <= ratio <= 2.0:
                    tech_scores.append(1.0) # Optimal
                elif ratio > 2.0:
                    tech_scores.append(0.7) # Overkill (diminishing returns)
                elif ratio < 1.0:
                     tech_scores.append(0.0) # Below spec (should be filtered but penalty here)

            if tech_scores:
                avg_tech_score = sum(tech_scores) / len(tech_scores)
                score += avg_tech_score * self.weights['technical_margin']
                if avg_tech_score > 0.8:
                    reasons.append("Good Spec Margin")
            
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


