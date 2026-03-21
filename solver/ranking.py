"""
Ranking Engine

Explainable multi-criteria ranking with score breakdown and transparency.
"""

import logging
import math
from typing import List, Dict, Any, Tuple
from core.models import OptimizationGoal, RequirementSpec

logger = logging.getLogger(__name__)


class RankingEngine:
    """Explainable multi-criteria ranking"""
    
    def __init__(self):
        """Initialize ranking engine with default weights"""
        self.optimization_weights = {
            OptimizationGoal.COST: {
                'headroom': 0.2,
                'ecosystem': 0.1,
                'lifecycle': 0.2,
                'cost': 0.5,
            },
            OptimizationGoal.POWER: {
                'headroom': 0.2,
                'ecosystem': 0.1,
                'lifecycle': 0.1,
                'power': 0.6,
            },
            OptimizationGoal.PERFORMANCE: {
                'headroom': 0.3,
                'ecosystem': 0.2,
                'lifecycle': 0.1,
                'performance': 0.4,
            },
            OptimizationGoal.BALANCED: {
                'headroom': 0.25,
                'ecosystem': 0.25,
                'lifecycle': 0.25,
                'cost': 0.25,
            },
        }
        
        # Curated ecosystem scores (manual initially, can be learned)
        self.ecosystem_scores = self._init_ecosystem_scores()
    
    def _init_ecosystem_scores(self) -> Dict[str, float]:
        """Initialize curated ecosystem scores per vendor/family"""
        return {
            # STMicroelectronics
            'STM32F4': 0.95,  # Excellent tooling, community, docs
            'STM32F7': 0.90,
            'STM32H7': 0.85,
            'STM32L4': 0.90,
            'STM32G4': 0.80,
            
            # Espressif
            'ESP32': 0.95,    # Excellent community, Arduino support
            'ESP32-S3': 0.90,
            'ESP32-C3': 0.85,
            
            # Nordic
            'nRF52': 0.90,    # Good SDK, BLE stack
            'nRF53': 0.85,
            
            # Raspberry Pi
            'RP2040': 0.95,   # Excellent docs, MicroPython support
            
            # Microchip
            'SAMD21': 0.85,
            'SAMD51': 0.80,
            
            # Texas Instruments
            'MSP430': 0.75,
            
            # Default
            'default': 0.50,
        }
    
    def rank(
        self,
        candidates: List[Dict[str, Any]],
        spec: RequirementSpec,
    ) -> List[Tuple[Dict[str, Any], float, Dict[str, float]]]:
        """
        Rank candidates by multi-criteria optimization.
        
        Args:
            candidates: List of candidate parts from hard filter
            spec: Requirement specification
        
        Returns:
            List of (candidate, total_score, score_breakdown) tuples, sorted by score
        """
        logger.info(f"Ranking {len(candidates)} candidates")
        
        # Get optimization weights
        weights = self.optimization_weights.get(
            spec.optimization_goal,
            self.optimization_weights[OptimizationGoal.BALANCED],
        )
        
        ranked = []
        
        for candidate in candidates:
            # Calculate score components
            score_breakdown = {}
            
            # Headroom score
            score_breakdown['headroom'] = self._calculate_headroom(candidate, spec)
            
            # Ecosystem score
            score_breakdown['ecosystem'] = self._calculate_ecosystem_score(candidate)
            
            # Lifecycle score
            score_breakdown['lifecycle'] = self._calculate_lifecycle_score(candidate)
            
            # Cost score (if available)
            if 'cost' in weights and candidate.get('cost_usd'):
                score_breakdown['cost'] = self._calculate_cost_score(candidate, spec)
            
            # Power score (if available)
            if 'power' in weights and candidate.get('standby_ua'):
                score_breakdown['power'] = self._calculate_power_score(candidate, spec)
            
            # Performance score
            if 'performance' in weights:
                score_breakdown['performance'] = self._calculate_performance_score(candidate, spec)
            
            # Calculate weighted total
            total_score = 0.0
            for component, weight in weights.items():
                if component in score_breakdown:
                    total_score += weight * score_breakdown[component]
            
            ranked.append((candidate, total_score, score_breakdown))
        
        # Sort by score (descending), then by MPN (ascending) for deterministic tie-breaking
        ranked.sort(key=lambda x: (-x[1], x[0]['mpn']))
        
        logger.info(f"Ranking complete. Top score: {ranked[0][1]:.3f}")
        
        return ranked
    
    def _calculate_headroom(
        self,
        candidate: Dict[str, Any],
        spec: RequirementSpec,
    ) -> float:
        """
        Calculate headroom score (extra resources beyond requirements).
        
        Returns:
            Score between 0.0 and 1.0
        """
        headroom_components = []
        
        # Flash headroom
        if 'flash_kb' in spec.hard_constraints:
            required = float(spec.hard_constraints['flash_kb'].get('min', 0))
            actual = float(candidate.get('flash_kb') or 0)
            if required > 0:
                headroom = (actual - required) / required
                headroom_components.append(min(headroom, 1.0))

        # RAM headroom
        if 'ram_kb' in spec.hard_constraints or 'sram_kb' in spec.hard_constraints:
            required = float(spec.hard_constraints.get('ram_kb', spec.hard_constraints.get('sram_kb', {})).get('min', 0))
            actual = float(candidate.get('sram_kb') or candidate.get('ram_kb') or 0)
            if required > 0:
                headroom = (actual - required) / required
                headroom_components.append(min(headroom, 1.0))

        # Peripheral headroom
        if spec.interfaces:
            for peripheral, min_count in spec.interfaces.items():
                field_name = f"{peripheral}_count"
                actual = float(candidate.get(field_name) or 0)
                min_count = float(min_count)
                if min_count > 0:
                    headroom = (actual - min_count) / min_count
                    headroom_components.append(min(headroom, 1.0))        
        # Average headroom
        if headroom_components:
            return sum(headroom_components) / len(headroom_components)
        
        return 0.5  # Neutral if no headroom constraints
    
    def _calculate_ecosystem_score(self, candidate: Dict[str, Any]) -> float:
        """
        Calculate ecosystem score (tooling, community, docs).
        
        Returns:
            Score between 0.0 and 1.0
        """
        family = candidate.get('family') or ''
        
        # Try exact match
        if family in self.ecosystem_scores:
            return self.ecosystem_scores[family]
        
        # Try prefix match (e.g., "STM32F405" -> "STM32F4")
        for key, score in self.ecosystem_scores.items():
            if family.startswith(key):
                return score
        
        # Default
        return self.ecosystem_scores['default']
    
    def _calculate_lifecycle_score(self, candidate: Dict[str, Any]) -> float:
        """
        Calculate lifecycle score (active > NRND > EOL).
        
        Returns:
            Score between 0.0 and 1.0
        """
        status = candidate.get('status') or 'unknown'
        
        lifecycle_map = {
            'active': 1.0,
            'nrnd': 0.5,  # Not Recommended for New Designs
            'eol': 0.1,   # End of Life
            'unknown': 0.3,
        }
        
        return lifecycle_map.get(status, 0.3)
    
    def _calculate_cost_score(
        self,
        candidate: Dict[str, Any],
        spec: RequirementSpec
    ) -> float:
        """
        Calculate cost score (lower is better).

        Returns:
            Score between 0.0 and 1.0
        """
        cost = float(candidate.get('cost_usd') or 0)

        if cost <= 0:
            return 0.5  # Neutral if no cost data
        
        # If there's a cost constraint, use it as reference
        if 'cost_usd' in spec.hard_constraints:
            max_cost = float(spec.hard_constraints['cost_usd'].get('max', 10.0))
        else:
            max_cost = 10.0  # Default reference
        
        # Normalize: lower cost = higher score
        normalized = 1.0 - (cost / max_cost)
        return max(0.0, min(1.0, normalized))
    
    def _calculate_power_score(
        self,
        candidate: Dict[str, Any],
        spec: RequirementSpec
    ) -> float:
        """
        Calculate power score (lower is better).

        Returns:
            Score between 0.0 and 1.0
        """
        standby_ua = float(candidate.get('standby_ua') or 0)

        if standby_ua <= 0:
            return 0.5  # Neutral if no power data
        
        # Reference: 10 µA is excellent, 1000 µA is poor
        # Use logarithmic scale
        normalized = 1.0 - (math.log10(standby_ua + 1) / math.log10(1000))
        return max(0.0, min(1.0, normalized))
    
    def _calculate_performance_score(
        self,
        candidate: Dict[str, Any],
        spec: RequirementSpec
    ) -> float:
        """
        Calculate performance score based on clocks and accelerators.

        Returns:
            Score between 0.0 and 1.0
        """
        components = []

        # Clock speed
        max_mhz = float(candidate.get('max_mhz') or 0)
        if max_mhz > 0:
            # Normalize: 500 MHz is excellent
            clock_score = min(max_mhz / 500.0, 1.0)
            components.append(clock_score)
        
        # FPU
        if candidate.get('has_fpu'):
            components.append(1.0)
        
        # DSP
        if candidate.get('has_dsp'):
            components.append(1.0)
        
        # Crypto
        if candidate.get('has_crypto'):
            components.append(1.0)
        
        if components:
            return sum(components) / len(components)
        
        return 0.5  # Neutral if no performance data
