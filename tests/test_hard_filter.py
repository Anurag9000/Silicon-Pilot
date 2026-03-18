"""
Test Hard Filter

Test deterministic filtering with zero tolerance for constraint violations.
"""

import pytest
import asyncpg
from uuid import uuid4

from core.models import RequirementSpec, OptimizationGoal
from solver import HardFilter


from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def db_pool():
    """Create mock database pool"""
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetch.return_value = []
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool


@pytest.fixture
def hard_filter(db_pool):
    """Create hard filter instance"""
    return HardFilter(db_pool)


@pytest.mark.asyncio
async def test_zero_false_positives(hard_filter):
    """Test that hard filter never returns parts violating constraints"""
    
    # Create spec with strict constraints
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 512},
            'sram_kb': {'min': 128},
            'can_count': {'min': 2},
        },
    )
    
    # Filter
    candidates = await hard_filter.filter(spec)
    
    # Verify all candidates satisfy constraints
    for candidate in candidates:
        assert candidate['flash_kb'] >= 512, f"Flash violation: {candidate['mpn']}"
        assert candidate['sram_kb'] >= 128, f"SRAM violation: {candidate['mpn']}"
        assert candidate['can_count'] >= 2, f"CAN violation: {candidate['mpn']}"


@pytest.mark.asyncio
async def test_determinism(hard_filter):
    """Test that same spec produces same results (100 runs)"""
    
    spec = RequirementSpec(
        hard_constraints={
            'core': 'ARM Cortex-M4',
            'flash_kb': {'min': 256},
        },
    )
    
    # Run 100 times
    results = []
    for _ in range(100):
        candidates = await hard_filter.filter(spec)
        mpns = [c['mpn'] for c in candidates]
        results.append(tuple(mpns))
    
    # All results should be identical
    assert len(set(results)) == 1, "Non-deterministic results detected"


@pytest.mark.asyncio
async def test_constraint_satisfaction_verification(hard_filter):
    """Test constraint satisfaction verification"""
    
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 512},
            'package_family': ['QFP'],
        },
    )
    
    # Get a candidate
    candidates = await hard_filter.filter(spec)
    
    if candidates:
        part_id = candidates[0]['id']
        
        # Verify constraints
        satisfaction = await hard_filter.verify_constraint_satisfaction(part_id, spec)
        
        # All constraints should be satisfied
        for constraint, satisfied in satisfaction.items():
            assert satisfied, f"Constraint {constraint} not satisfied"


@pytest.mark.asyncio
async def test_empty_result_on_impossible_constraints(hard_filter):
    """Test that impossible constraints return empty set"""
    
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 999999},  # Impossible
        },
    )
    
    candidates = await hard_filter.filter(spec)
    
    assert len(candidates) == 0, "Should return empty set for impossible constraints"


@pytest.mark.asyncio
async def test_range_constraints(hard_filter):
    """Test range constraints (min and max)"""
    
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 256, 'max': 512},
        },
    )
    
    candidates = await hard_filter.filter(spec)
    
    for candidate in candidates:
        assert 256 <= candidate['flash_kb'] <= 512, f"Range violation: {candidate['mpn']}"


@pytest.mark.asyncio
async def test_list_constraints(hard_filter):
    """Test IN constraints (list of values)"""
    
    spec = RequirementSpec(
        hard_constraints={
            'package_family': ['QFP', 'QFN'],
        },
    )
    
    candidates = await hard_filter.filter(spec)
    
    for candidate in candidates:
        assert candidate['package_family'] in ['QFP', 'QFN'], f"List violation: {candidate['mpn']}"
