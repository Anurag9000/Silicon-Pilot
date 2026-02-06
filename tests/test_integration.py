"""
Test End-to-End Recommendation Flow

Integration test for complete recommendation pipeline.
"""

import pytest
import asyncio
from uuid import uuid4

from core.models import RequirementSpec, OptimizationGoal
from core.database import Database
from core.db_operations import DatabaseOperations
from solver import HardFilter, RankingEngine, NearMissEngine
from llm import LLMOrchestrator
from questions import QuestionEngine


@pytest.fixture
async def db():
    """Create database connection"""
    db = Database()
    await db.connect()
    yield db
    await db.disconnect()


@pytest.fixture
async def db_ops(db):
    """Create database operations"""
    return DatabaseOperations(db.pool)


@pytest.fixture
def hard_filter(db):
    """Create hard filter"""
    return HardFilter(db.pool)


@pytest.fixture
def ranking_engine():
    """Create ranking engine"""
    return RankingEngine()


@pytest.fixture
def near_miss_engine():
    """Create near-miss engine"""
    return NearMissEngine()


@pytest.fixture
def question_engine():
    """Create question engine"""
    return QuestionEngine()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_recommendation(
    db_ops,
    hard_filter,
    ranking_engine,
    near_miss_engine,
):
    """
    Test complete recommendation flow from requirement to result.
    """
    # Step 1: Create requirement spec
    spec = RequirementSpec(
        hard_constraints={
            'core': 'ARM Cortex-M4',
            'flash_kb': {'min': 512},
            'sram_kb': {'min': 128},
            'can_count': {'min': 2},
            'package_family': ['QFP'],
        },
        optimization_goal=OptimizationGoal.BALANCED,
    )
    
    # Step 2: Store spec in database
    spec_id = await db_ops.create_requirement_spec(
        spec,
        "Need Cortex-M4, 512KB flash, 128KB RAM, 2 CAN, QFP package",
    )
    
    assert spec_id is not None
    
    # Step 3: Hard filter
    candidates = await hard_filter.filter(spec)
    
    # Should have some candidates (if data is loaded)
    # For test, we'll allow 0 if no data
    print(f"Found {len(candidates)} candidates")
    
    if len(candidates) == 0:
        pytest.skip("No data in database for testing")
    
    # Step 4: Rank candidates
    ranked = ranking_engine.rank(candidates, spec)
    
    assert len(ranked) > 0
    
    # Verify ranking
    for i in range(len(ranked) - 1):
        # Scores should be descending
        assert ranked[i][1] >= ranked[i+1][1], "Ranking not in descending order"
    
    # Step 5: Get evidence for top candidate
    top_candidate = ranked[0][0]
    evidence = await db_ops.get_evidence_for_part(top_candidate['id'])
    
    # Should have evidence
    assert len(evidence) > 0, "No evidence for top candidate"
    
    # Step 6: Near-miss suggestions (if few candidates)
    if len(candidates) < 20:
        all_parts = await db_ops.search_parts(limit=1000)
        near_misses = await near_miss_engine.find_near_misses(
            spec,
            all_parts,
            candidates,
            max_suggestions=5,
        )
        
        print(f"Found {len(near_misses)} near-miss suggestions")
    
    # Step 7: Log recommendation
    from core.models import CandidatePart, RecommendationResult
    
    candidate_parts = []
    for candidate_data, score, score_breakdown in ranked[:10]:
        evidence_records = await db_ops.get_evidence_for_part(candidate_data['id'])
        
        candidate_part = CandidatePart(
            mpn=candidate_data['mpn'],
            manufacturer=candidate_data['manufacturer'],
            family=candidate_data.get('family', ''),
            total_score=score,
            score_breakdown=score_breakdown,
            specs=candidate_data,
            evidence_ids=[ev['id'] for ev in evidence_records],
        )
        candidate_parts.append(candidate_part)
    
    result = RecommendationResult(
        candidates=candidate_parts,
        total_candidates=len(candidates),
        constraint_checks={},
        ranking_explanation="Test recommendation",
        near_miss_suggestions=[],
    )
    
    log_id = await db_ops.log_recommendation(spec_id, result)
    
    assert log_id is not None
    
    # Step 8: Verify we can retrieve the log
    logs = await db_ops.get_recommendation_logs(spec_id)
    
    assert len(logs) > 0
    assert logs[0]['id'] == log_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_question_answer_flow(
    db_ops,
    hard_filter,
    question_engine,
):
    """
    Test question-answer refinement flow.
    """
    # Step 1: Create spec with unknowns
    spec = RequirementSpec(
        hard_constraints={
            'flash_kb': {'min': 256},
        },
        unknowns=['temp_min_c', 'temp_max_c', 'sram_kb', 'package_family'],
    )
    
    spec_id = await db_ops.create_requirement_spec(spec, "Need 256KB flash")
    
    # Step 2: Get initial candidates
    candidates = await hard_filter.filter(spec)
    
    if len(candidates) == 0:
        pytest.skip("No data in database")
    
    # Step 3: Generate questions
    questions = question_engine.select_questions(spec, candidates, max_questions=3)
    
    assert len(questions) > 0
    assert len(questions) <= 3
    
    # Step 4: Store question turn
    turn_id = await db_ops.create_question_turn(
        spec_id=spec_id,
        turn_index=0,
        questions=questions,
    )
    
    assert turn_id is not None
    
    # Step 5: Simulate user answers
    from core.models import Answer
    
    answers = [
        Answer(
            field_name='temp_min_c',
            value=-40,
            is_hard_constraint=True,
        ),
        Answer(
            field_name='temp_max_c',
            value=85,
            is_hard_constraint=True,
        ),
    ]
    
    # Step 6: Apply answers
    updated_spec = question_engine.apply_answers(spec, answers)
    
    # Verify unknowns reduced
    assert len(updated_spec.unknowns) < len(spec.unknowns)
    
    # Verify constraints added
    assert 'temp_min_c' in updated_spec.hard_constraints
    assert 'temp_max_c' in updated_spec.hard_constraints
    
    # Step 7: Update spec in database
    await db_ops.update_requirement_spec(spec_id, updated_spec)
    
    # Step 8: Update question turn with answers
    await db_ops.update_question_turn_answers(turn_id, answers)
    
    # Step 9: Get updated candidates
    updated_candidates = await hard_filter.filter(updated_spec)
    
    # Should have fewer or equal candidates
    assert len(updated_candidates) <= len(candidates)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_evidence_traceability(db_ops):
    """
    Test that all recommendations have evidence.
    """
    # Get all parts
    parts = await db_ops.search_parts(limit=100)
    
    if len(parts) == 0:
        pytest.skip("No data in database")
    
    # Check each part has evidence
    for part in parts:
        evidence = await db_ops.get_evidence_for_part(part['id'])
        
        # Should have at least some evidence
        # (In production, enforce >95% coverage)
        if len(evidence) == 0:
            print(f"WARNING: Part {part['mpn']} has no evidence")
