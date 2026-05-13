"""
ML-Based Ranker

Uses LightGBM to rank search results based on user feedback.

Features extracted:
- Part specs (Flash, RAM, frequency, peripherals)
- Cost (when available)
- Availability
- Manufacturer popularity
- Spec completeness
- Query relevance

Hybrid scoring:
- 70% deterministic (rule-based)
- 30% ML-based (learned from user selections)

Training:
- Uses user_selections table for training data
- Learns from selection rank (position in results)
- Optimizes for NDCG (Normalized Discounted Cumulative Gain)
"""

import asyncpg
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
import json


@dataclass
class RankingFeatures:
    """Features for ranking"""
    # Part specs
    flash_kb: float
    ram_kb: float
    max_freq_mhz: float
    peripheral_count: int
    
    # Metadata
    manufacturer_popularity: float  # 0-1
    spec_completeness: float  # 0-1
    
    # Query relevance
    query_match_score: float  # 0-1
    
    # Cost/Availability (when available)
    cost_score: float  # 0-1 (lower cost = higher score)
    availability_score: float  # 0-1


class MLRanker:
    """ML-based ranking engine"""
    
    def __init__(self, db_pool):
        # Accepts either an asyncpg.Pool (preferred) or a URL string (legacy)
        if isinstance(db_pool, str):
            import warnings
            warnings.warn(
                "MLRanker: pass an asyncpg.Pool, not a URL string.",
                DeprecationWarning,
                stacklevel=2,
            )
            self._db_url  = db_pool
            self.db_pool  = None   # created lazily in _get_pool()
        else:
            self._db_url  = None
            self.db_pool  = db_pool
        self.model = None
        self.feature_names = [
            'flash_kb', 'sram_kb', 'max_mhz', 'peripheral_count',
            'manufacturer_popularity', 'spec_completeness',
            'query_match_score', 'cost_score', 'availability_score'
        ]

    async def _get_pool(self):
        """Return pool, creating one from URL if needed."""
        if self.db_pool is None:
            self.db_pool = await asyncpg.create_pool(self._db_url, min_size=1, max_size=5)
        return self.db_pool
    
    async def extract_features(self, part_id: uuid.UUID,
                              query_text: str = "") -> Optional[RankingFeatures]:
        """Extract features for a part"""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Explicit columns to avoid SELECT p.* collision (both tables have 'id')
            part = await conn.fetchrow("""
                SELECT p.id            AS part_id,
                       p.mpn,
                       p.manufacturer,
                       p.status,
                       m.flash_kb,
                       m.sram_kb,
                       m.max_mhz,
                       m.uart_count,
                       m.spi_count,
                       m.i2c_count,
                       m.can_count,
                       m.usb_fs,
                       m.usb_hs,
                       m.adc_channels,
                       m.dac_channels,
                       m.timers_count,
                       m.cost_usd
                FROM parts p
                LEFT JOIN mcu_specs m ON p.id = m.part_id
                WHERE p.id = $1
            """, part_id)

            if not part:
                return None

            # Derive a peripheral count from available columns
            peripheral_count = sum([
                part['uart_count']  or 0,
                part['spi_count']   or 0,
                part['i2c_count']   or 0,
                part['can_count']   or 0,
                int(bool(part['usb_fs'])) + int(bool(part['usb_hs'])),
                part['adc_channels'] or 0,
                part['dac_channels'] or 0,
                part['timers_count'] or 0,
            ])

            manufacturer_popularity = {
                'STMicroelectronics': 0.9,
                'NXP': 0.8,
                'Texas Instruments': 0.85,
                'Microchip': 0.75,
                'Analog Devices': 0.8,
            }.get(part['manufacturer'], 0.5)

            # Spec completeness — only fields we actually store
            spec_fields = ['flash_kb', 'sram_kb', 'max_mhz']
            filled_fields = sum(1 for f in spec_fields if part[f] is not None)
            spec_completeness = filled_fields / len(spec_fields)

            query_match_score = 0.5
            if query_text:
                query_lower = query_text.lower()
                if part['mpn'].lower() in query_lower or query_lower in part['mpn'].lower():
                    query_match_score = 1.0
                elif part['manufacturer'].lower() in query_lower:
                    query_match_score = 0.7

            cost_score        = 0.7
            availability_score = 0.8

            return RankingFeatures(
                flash_kb=float(part['flash_kb'] or 0),
                ram_kb=float(part['sram_kb'] or 0),
                max_freq_mhz=float(part['max_mhz'] or 0),
                peripheral_count=peripheral_count,
                manufacturer_popularity=manufacturer_popularity,
                spec_completeness=spec_completeness,
                query_match_score=query_match_score,
                cost_score=cost_score,
                availability_score=availability_score,
            )
    
    def features_to_vector(self, features: RankingFeatures) -> np.ndarray:
        """Convert features to numpy vector"""
        return np.array([
            features.flash_kb,
            features.ram_kb,
            features.max_freq_mhz,
            features.peripheral_count,
            features.manufacturer_popularity,
            features.spec_completeness,
            features.query_match_score,
            features.cost_score,
            features.availability_score
        ])
    
    def calculate_deterministic_score(self, features: RankingFeatures) -> float:
        """
        Calculate deterministic score (rule-based)
        
        Weights:
        - Spec completeness: 20%
        - Query match: 30%
        - Manufacturer: 15%
        - Cost: 20%
        - Availability: 15%
        """
        score = (
            features.spec_completeness * 20 +
            features.query_match_score * 30 +
            features.manufacturer_popularity * 15 +
            features.cost_score * 20 +
            features.availability_score * 15
        )
        return score
    
    def calculate_ml_score(self, features: RankingFeatures) -> float:
        """
        Calculate ML score (placeholder - would use trained LightGBM model)
        
        In production, this would:
        1. Load trained LightGBM model
        2. Predict score from features
        3. Return normalized score
        """
        # Placeholder: simple weighted combination
        feature_vec = self.features_to_vector(features)
        
        # Simulated learned weights (would come from trained model)
        weights = np.array([0.15, 0.15, 0.10, 0.10, 0.15, 0.10, 0.15, 0.05, 0.05])
        
        # Normalize features
        feature_vec_norm = feature_vec / (np.max(feature_vec) + 1e-6)
        
        score = np.dot(feature_vec_norm, weights) * 100
        return float(score)
    
    async def rank_parts(self, part_ids: List[uuid.UUID],
                        query_text: str = "",
                        hybrid_weight: float = 0.7) -> List[Tuple[uuid.UUID, float]]:
        """
        Rank parts using hybrid scoring
        
        Args:
            part_ids: List of part IDs to rank
            query_text: Search query
            hybrid_weight: Weight for deterministic score (0.7 = 70% deterministic, 30% ML)
        
        Returns:
            List of (part_id, score) tuples, sorted by score descending
        """
        ranked = []
        
        for part_id in part_ids:
            features = await self.extract_features(part_id, query_text)
            
            if not features:
                continue
            
            # Hybrid scoring
            deterministic_score = self.calculate_deterministic_score(features)
            ml_score = self.calculate_ml_score(features)
            
            final_score = (
                hybrid_weight * deterministic_score +
                (1 - hybrid_weight) * ml_score
            )
            
            ranked.append((part_id, final_score))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    async def log_selection(self, session_id: uuid.UUID,
                           query_text: str,
                           results_shown: List[uuid.UUID],
                           selected_part_id: uuid.UUID) -> uuid.UUID:
        """Log user selection for training (requires user_selections table)."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            selection_rank = None
            for i, pid in enumerate(results_shown, 1):
                if pid == selected_part_id:
                    selection_rank = i
                    break

            selection_id = await conn.fetchval("""
                INSERT INTO user_selections (
                    session_id, query_text, query_type,
                    results_shown, result_count,
                    selected_part_id, selection_rank
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, session_id, query_text, 'search',
                results_shown, len(results_shown),
                selected_part_id, selection_rank)

            return selection_id
    
    async def get_training_data(self, limit: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """Get training data from user selections."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            selections = await conn.fetch("""
                SELECT selected_part_id, selection_rank, query_text
                FROM user_selections
                WHERE selected_part_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)

            features_list = []
            labels_list   = []

            for sel in selections:
                feats = await self.extract_features(
                    sel['selected_part_id'],
                    sel['query_text'] or ""
                )
                if feats:
                    features_list.append(self.features_to_vector(feats))
                    label = 1.0 / (sel['selection_rank'] or 1)
                    labels_list.append(label)

            if not features_list:
                return np.array([]), np.array([])

            return np.array(features_list), np.array(labels_list)


# Example usage
async def main():
    import os
    db_url = os.environ["DATABASE_URL"]
    ranker = MLRanker(db_url)
    
    # Example: Rank parts
    # part_ids = [uuid.UUID("..."), uuid.UUID("..."), ...]
    # ranked = await ranker.rank_parts(part_ids, query_text="STM32F4 high performance")
    # 
    # for part_id, score in ranked:
    #     print(f"{part_id}: {score:.2f}")


if __name__ == "__main__":
    import asyncio
    import sys
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
