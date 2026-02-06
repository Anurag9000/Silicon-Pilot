"""
FastAPI Server

Main API server with endpoints for recommendations, parts, evidence, and questions.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import asyncpg

from core import (
    Database,
    DatabaseOperations,
    RequirementSpec,
    Answer,
    ParseRequirementsRequest,
    ParseRequirementsResponse,
    AnswerQuestionsRequest,
    AnswerQuestionsResponse,
    RecommendRequest,
    CandidatePart,
    RecommendationResult,
)
from solver import HardFilter, RankingEngine, NearMissEngine
from llm import LLMOrchestrator
from questions import QuestionEngine

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Global instances
db = Database()
db_ops: Optional[DatabaseOperations] = None
hard_filter: Optional[HardFilter] = None
ranking_engine: Optional[RankingEngine] = None
near_miss_engine: Optional[NearMissEngine] = None
llm_orchestrator: Optional[LLMOrchestrator] = None
question_engine: Optional[QuestionEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global db_ops, hard_filter, ranking_engine, near_miss_engine, llm_orchestrator, question_engine
    
    # Startup
    logger.info("Starting HardwareGenius API")
    
    # Connect to database
    await db.connect()
    
    # Initialize components
    db_ops = DatabaseOperations(db.pool)
    hard_filter = HardFilter(db.pool)
    ranking_engine = RankingEngine()
    near_miss_engine = NearMissEngine()
    llm_orchestrator = LLMOrchestrator(
        api_key=os.getenv('OPENAI_API_KEY'),
    )
    question_engine = QuestionEngine()
    
    logger.info("All components initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HardwareGenius API")
    await db.disconnect()


# Create FastAPI app
app = FastAPI(
    title="HardwareGenius API",
    description="Evidence-backed, deterministic hardware component recommendation system",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Check ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = await db_ops.get_stats()
    return {
        "status": "healthy",
        "database": "connected",
        "stats": stats,
    }


# ==================== Requirements Parsing ====================

@app.post("/spec/from_text", response_model=ParseRequirementsResponse)
async def parse_requirements(request: ParseRequirementsRequest):
    """
    Parse natural language requirements into structured RequirementSpec.
    
    This endpoint uses LLM to extract constraints from user text.
    """
    try:
        # Parse with LLM
        spec = await llm_orchestrator.parse_requirements(request.text)
        
        # Store in database
        spec_id = await db_ops.create_requirement_spec(spec, request.text)
        
        # Get initial candidate count
        candidates = await hard_filter.filter(spec)
        
        # Generate initial questions if there are unknowns
        questions = []
        if spec.unknowns:
            questions = await llm_orchestrator.generate_questions(
                spec,
                len(candidates),
            )
            
            # Store question turn
            if questions:
                await db_ops.create_question_turn(
                    spec_id=spec_id,
                    turn_index=0,
                    questions=questions,
                )
        
        return ParseRequirementsResponse(
            spec_id=spec_id,
            spec=spec,
            questions=questions,
            candidates_count=len(candidates),
        )
    
    except Exception as e:
        logger.error(f"Error parsing requirements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Question Answering ====================

@app.post("/spec/answer", response_model=AnswerQuestionsResponse)
async def answer_questions(request: AnswerQuestionsRequest):
    """
    Apply user answers to update RequirementSpec and get next questions.
    """
    try:
        # Get current spec
        spec = await db_ops.get_requirement_spec(request.spec_id)
        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")
        
        # Apply answers
        updated_spec = question_engine.apply_answers(spec, request.answers)
        
        # Update in database
        await db_ops.update_requirement_spec(request.spec_id, updated_spec)
        
        # Get updated candidates
        candidates = await hard_filter.filter(updated_spec)
        
        # Check stop criteria
        previous_turns = await db_ops.get_question_turns(request.spec_id)
        should_stop = False
        
        if len(previous_turns) > 0:
            # Get previous top-N
            prev_candidates = []  # Would need to fetch from previous recommendation
            # For now, just check if unknowns are empty
            should_stop = len(updated_spec.unknowns) == 0
        
        # Generate next questions if not stopping
        next_questions = []
        if not should_stop and updated_spec.unknowns:
            next_questions = question_engine.select_questions(
                updated_spec,
                candidates,
            )
            
            # Store question turn
            if next_questions:
                turn_index = len(previous_turns)
                await db_ops.create_question_turn(
                    spec_id=request.spec_id,
                    turn_index=turn_index,
                    questions=next_questions,
                )
        
        return AnswerQuestionsResponse(
            spec=updated_spec,
            questions=next_questions,
            candidates_count=len(candidates),
            ready_for_recommendation=should_stop or len(updated_spec.unknowns) == 0,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error answering questions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Recommendations ====================

@app.post("/recommend", response_model=RecommendationResult)
async def recommend(request: RecommendRequest):
    """
    Get hardware recommendations based on RequirementSpec.
    
    This is the core recommendation endpoint with deterministic filtering
    and explainable ranking.
    """
    try:
        # Get spec
        spec = await db_ops.get_requirement_spec(request.spec_id)
        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")
        
        # Hard filter (zero tolerance)
        candidates = await hard_filter.filter(spec)
        
        if not candidates:
            return RecommendationResult(
                candidates=[],
                total_candidates=0,
                constraint_checks={},
                ranking_explanation="No parts match all hard constraints",
                near_miss_suggestions=[],
            )
        
        # Rank candidates
        ranked = ranking_engine.rank(candidates, spec)
        
        # Build CandidatePart objects with evidence
        candidate_parts = []
        for candidate_data, score, score_breakdown in ranked[:request.max_results]:
            # Get evidence for this part
            evidence_records = await db_ops.get_evidence_for_part(
                candidate_data['id']
            )
            
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
        
        # Generate explanation
        if candidate_parts:
            explanation = await llm_orchestrator.generate_explanation(
                spec,
                candidates,
                ranked[0][0],
            )
        else:
            explanation = "No candidates found"
        
        # Find near-miss suggestions
        near_miss_suggestions = []
        if len(candidates) < 20:  # Only if we have few matches
            # Get all parts for near-miss analysis
            all_parts = await db_ops.search_parts(limit=1000)
            
            near_miss_suggestions = await near_miss_engine.find_near_misses(
                spec,
                all_parts,
                candidates,
                max_suggestions=5,
            )
        
        # Build constraint checks
        constraint_checks = {}
        for field, value in spec.hard_constraints.items():
            constraint_checks[field] = {
                'required': value,
                'satisfied': len(candidates) > 0,
            }
        
        result = RecommendationResult(
            candidates=candidate_parts,
            total_candidates=len(candidates),
            constraint_checks=constraint_checks,
            ranking_explanation=explanation,
            near_miss_suggestions=near_miss_suggestions,
        )
        
        # Log recommendation
        await db_ops.log_recommendation(request.spec_id, result)
        
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Parts ====================

@app.get("/parts/{mpn}")
async def get_part(mpn: str):
    """Get part details by MPN"""
    try:
        part = await db_ops.get_part_by_mpn(mpn)
        
        if not part:
            raise HTTPException(status_code=404, detail="Part not found")
        
        # Get evidence
        evidence = await db_ops.get_evidence_for_part(part['id'])
        
        return {
            "part": part,
            "evidence": evidence,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting part: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parts")
async def search_parts(
    manufacturer: Optional[str] = None,
    family: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
):
    """Search parts with filters"""
    try:
        parts = await db_ops.search_parts(
            manufacturer=manufacturer,
            family=family,
            status=status,
            limit=limit,
        )
        
        return {
            "parts": parts,
            "count": len(parts),
        }
    
    except Exception as e:
        logger.error(f"Error searching parts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Evidence ====================

@app.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: UUID):
    """Get evidence details by ID"""
    try:
        evidence = await db_ops.get_evidence_by_id(evidence_id)
        
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        return evidence
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin ====================

@app.get("/admin/stats")
async def get_stats():
    """Get database statistics"""
    try:
        stats = await db_ops.get_stats()
        return stats
    
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/conflicts")
async def get_conflicts(limit: int = 100):
    """Get open conflicts for review"""
    try:
        conflicts = await db_ops.get_open_conflicts(limit=limit)
        return {
            "conflicts": conflicts,
            "count": len(conflicts),
        }
    
    except Exception as e:
        logger.error(f"Error getting conflicts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
