"""
Test Ranking Engine

Test explainable multi-criteria ranking.
"""

import pytest

from core.models import RequirementSpec, OptimizationGoal
from solver import RankingEngine


@pytest.fixture
def ranking_engine():
    """Create ranking engine instance"""
    return RankingEngine()


@pytest.fixture
def sample_candidates():
    """Create sample candidates for testing"""
    return [
        {
            'mpn': 'STM32F405RGT6',
            'manufacturer': 'STMicroelectronics',
            'family': 'STM32F4',
            'flash_kb': 1024,
            'sram_kb': 192,
            'can_count': 2,
            'max_mhz': 168,
            'has_fpu': True,
            'status': 'active',
            'cost_usd': 5.50,
        },
        {
            'mpn': 'STM32F407VGT6',
            'manufacturer': 'STMicroelectronics',
            'family': 'STM32F4',
            'flash_kb': 1024,
            'sram_kb': 192,
            'can_count': 2,
            'max_mhz': 168,
            'has_fpu': True,
            'status': 'active',
            'cost_usd': 6.00,
        },
        {
            'mpn': 'ESP32-S3',
            'manufacturer': 'Espressif',
            'family': 'ESP32',
            'flash_kb': 512,
            'sram_kb': 512,
            'can_count': 0,
            'max_mhz': 240,
            'has_fpu': False,
            'status': 'active',
            'cost_usd': 0.10,
            'has_wireless': True,
        },
    ]


def test_score_components(ranking_engine, sample_candidates):
    """Test that all score components are calculated"""
    
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 512},
        },
        optimization_goal=OptimizationGoal.BALANCED,
    )
    
    ranked = ranking_engine.rank(sample_candidates, spec)
    
    for candidate, score, breakdown in ranked:
        # Check that score breakdown exists
        assert 'headroom' in breakdown
        assert 'ecosystem' in breakdown
        assert 'lifecycle' in breakdown
        
        # Check that scores are in valid range
        for component, value in breakdown.items():
            assert 0.0 <= value <= 1.0, f"Score {component} out of range: {value}"


def test_optimization_goals(ranking_engine, sample_candidates):
    """Test different optimization goals produce different rankings"""
    
    spec_cost = RequirementSpec(
        hard_constraints={'flash_kb': {'min': 512}},
        optimization_goal=OptimizationGoal.COST,
    )
    
    spec_performance = RequirementSpec(
        hard_constraints={'flash_kb': {'min': 512}},
        optimization_goal=OptimizationGoal.PERFORMANCE,
    )
    
    ranked_cost = ranking_engine.rank(sample_candidates, spec_cost)
    ranked_perf = ranking_engine.rank(sample_candidates, spec_performance)
    
    # Top candidates should be different
    top_cost = ranked_cost[0][0]['mpn']
    top_perf = ranked_perf[0][0]['mpn']
    
    # ESP32 should rank higher for cost, STM32 for performance
    assert top_cost == 'ESP32-S3', "Cost optimization should favor ESP32"
    assert top_perf in ['STM32F405RGT6', 'STM32F407VGT6'], "Performance optimization should favor STM32"


def test_tie_breaking(ranking_engine):
    """Test deterministic tie-breaking by MPN"""
    
    # Create identical candidates with different MPNs
    candidates = [
        {
            'mpn': 'PART_B',
            'manufacturer': 'Vendor',
            'family': 'Family',
            'flash_kb': 512,
            'sram_kb': 128,
            'status': 'active',
        },
        {
            'mpn': 'PART_A',
            'manufacturer': 'Vendor',
            'family': 'Family',
            'flash_kb': 512,
            'sram_kb': 128,
            'status': 'active',
        },
    ]
    
    spec = RequirementSpec(
        hard_constraints={'flash_kb': {'min': 512}},
    )
    
    ranked = ranking_engine.rank(candidates, spec)
    
    # Should be sorted by MPN (ascending) for tie-breaking
    assert ranked[0][0]['mpn'] == 'PART_A'
    assert ranked[1][0]['mpn'] == 'PART_B'


def test_headroom_calculation(ranking_engine):
    """Test headroom score calculation"""
    
    candidates = [
        {
            'mpn': 'HIGH_HEADROOM',
            'manufacturer': 'Vendor',
            'family': 'Family',
            'flash_kb': 2048,  # 4x requirement
            'sram_kb': 512,    # 4x requirement
            'status': 'active',
        },
        {
            'mpn': 'LOW_HEADROOM',
            'manufacturer': 'Vendor',
            'family': 'Family',
            'flash_kb': 512,   # Exactly requirement
            'sram_kb': 128,    # Exactly requirement
            'status': 'active',
        },
    ]
    
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 512},
            'sram_kb': {'min': 128},
        },
    )
    
    ranked = ranking_engine.rank(candidates, spec)
    
    # High headroom should rank higher
    assert ranked[0][0]['mpn'] == 'HIGH_HEADROOM'
    
    # Check headroom scores
    high_headroom_score = ranked[0][2]['headroom']
    low_headroom_score = ranked[1][2]['headroom']
    
    assert high_headroom_score > low_headroom_score


def test_lifecycle_score(ranking_engine):
    """Test lifecycle scoring (active > NRND > EOL)"""
    
    candidates = [
        {'mpn': 'ACTIVE', 'manufacturer': 'V', 'family': 'F', 'flash_kb': 512, 'status': 'active'},
        {'mpn': 'NRND', 'manufacturer': 'V', 'family': 'F', 'flash_kb': 512, 'status': 'nrnd'},
        {'mpn': 'EOL', 'manufacturer': 'V', 'family': 'F', 'flash_kb': 512, 'status': 'eol'},
    ]
    
    spec = RequirementSpec(hard_constraints={'flash_kb': {'min': 512}})
    
    ranked = ranking_engine.rank(candidates, spec)
    
    # Active should rank highest
    assert ranked[0][0]['mpn'] == 'ACTIVE'
    
    # Check lifecycle scores
    assert ranked[0][2]['lifecycle'] > ranked[1][2]['lifecycle']
    assert ranked[1][2]['lifecycle'] > ranked[2][2]['lifecycle']
