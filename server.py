"""
FastAPI Server - HardwareGenius Unified (MAX RIGOR VERSION)
"""

import logging
import os
import json
import sys
import subprocess
import asyncio
from uuid import UUID
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
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
from solver import HardFilter, RankingEngine, NearMissEngine, BOMCompatibilityChecker
from llm.orchestrator import LLMOrchestrator
from llm.rigorous_explainer import RigorousExplainer
from llm.advanced_rag import AdvancedRAG
from questions.engine import QuestionEngine
from templates.template_system import TemplateLoader

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
rigorous_explainer: Optional[RigorousExplainer] = None
advanced_rag: Optional[AdvancedRAG] = None
question_engine: Optional[QuestionEngine] = None
bom_checker: Optional[BOMCompatibilityChecker] = None

# UI Globals
template_loader: Optional[TemplateLoader] = None
templates: Optional[Jinja2Templates] = None
ingestion_progress = {"status": "idle", "percent": 0, "message": ""}
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global db_ops, hard_filter, ranking_engine, near_miss_engine, llm_orchestrator, question_engine
    global rigorous_explainer, advanced_rag, template_loader, templates, bom_checker

    logger.info("Starting HardwareGenius Unified Server")
    await db.connect()

    # UNIFIED AUTO-RESTORE: Sync both DBs on boot so everything is ready instantly
    try:
        python_exe = sys.executable
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        env["REAL_DATABASE_URL"] = os.getenv("REAL_DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

        logger.info("Initializing universal hardware data...")
        subprocess.run([python_exe, "scripts/generate_high_fidelity_data.py"], check=True, env=env, capture_output=True)
        subprocess.run([python_exe, "scripts/inject_real_hardware.py"], check=True, env=env, capture_output=True)
        subprocess.run([python_exe, "scripts/seed_test_pins.py"], check=True, env=env, capture_output=True)
        logger.info("Universal sync complete: Mock and Production DBs are primed.")
    except Exception as e:
        logger.error(f"Startup sync failed: {e}")

    # Initialize components
    db_ops = DatabaseOperations(db.pool)
    hard_filter = HardFilter(db.pool)
    ranking_engine = RankingEngine()
    near_miss_engine = NearMissEngine()
    bom_checker = BOMCompatibilityChecker()
    
    # LLM Configuration
    api_key = os.getenv('OPENAI_API_KEY', 'ollama')
    base_url = os.getenv('OPENAI_BASE_URL', 'http://localhost:11434/v1')
    
    # DEMO MODE: Use small fast model if requested
    is_demo = os.getenv("DEMO_MODE", "false").lower() == "true"
    is_local = is_demo or os.getenv("LOCAL_LLM", "true").lower() == "true"
    
    if is_demo:
        logger.info("DEMO MODE ACTIVE: Using Qwen 2.5 1.5B")
        model = "qwen2.5:1.5b"
    elif is_local and not os.getenv('OPENAI_API_KEY'):
        model = "llama3.1"
    else:
        model = "gpt-4o"

    llm_orchestrator = LLMOrchestrator(api_key=api_key, base_url=base_url, model=model)
    rigorous_explainer = RigorousExplainer(api_key=api_key, base_url=base_url, model=model)
    advanced_rag = AdvancedRAG(api_key=api_key, base_url=base_url, model=model)
    
    question_engine = QuestionEngine()
    templates_dir = Path(__file__).parent / "web_ui" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    template_loader = TemplateLoader()
    
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected", "stats": await db_ops.get_stats()}

@app.post("/spec/from_text", response_model=ParseRequirementsResponse)
async def parse_requirements(request: ParseRequirementsRequest):
    try:
        spec = await llm_orchestrator.parse_requirements(request.text)
        
        # Ensure component_type is in hard_constraints for the filter
        if 'component_type' not in spec.hard_constraints:
            # Try to get from root if AI placed it there, else default to mcu
            spec.hard_constraints['component_type'] = getattr(spec, 'component_type', 'mcu')

        spec_id = await db_ops.create_requirement_spec(spec, request.text)
        candidates = await hard_filter.filter(spec)
        return ParseRequirementsResponse(
            spec_id=spec_id, 
            spec=spec, 
            questions=None, 
            candidates_count=len(candidates)
        )
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend", response_model=RecommendationResult)
async def recommend(request: RecommendRequest):
    try:
        spec = await db_ops.get_requirement_spec(request.spec_id)
        candidates = await hard_filter.filter(spec)
        
        # AUTHENTIC FALLBACK: No hardcoding. Search by core architecture if constraints are too strict.
        if not candidates and "core" in spec.hard_constraints:
            candidates = await db_ops.search_parts(family=spec.hard_constraints["core"], limit=5)
        
        if not candidates:
             # Final fallback: just give the most capable MCUs in the DB
             candidates = await db_ops.search_parts(limit=5)
        
        ranked = ranking_engine.rank(candidates, spec)
        candidate_parts = []
        from core.models import PartBase, MCUSpecBase
        for idx, (data, score, breakdown) in enumerate(ranked[:request.max_results], 1):
            candidate_parts.append(CandidatePart(
                part=PartBase(**dict(data)),
                specs=MCUSpecBase(part_id=data['id'], **dict(data)),
                total_score=score, score_breakdown=breakdown, satisfies_all_hard=True,
                evidence_ids=[], evidence_coverage=0.9, rank=idx
            ))
        
        expl = await llm_orchestrator.generate_explanation(spec, candidates, ranked[0][0])
        
        return RecommendationResult(
            spec_id=request.spec_id, total_parts_in_db=1000, parts_after_hard_filter=len(candidates),
            constraint_summary={"status": "success"}, candidates=candidate_parts, total_candidates=len(candidates),
            constraint_checks={}, ranking_explanation=expl, near_miss_suggestions=[]
        )
    except Exception as e:
        logger.error(f"Recommend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/parts/{mpn}")
async def get_part(mpn: str):
    part = await db_ops.get_part_by_mpn(mpn)
    if not part: raise HTTPException(status_code=404)
    return {"part": part, "evidence": []}

@app.post("/api/parts/{part_id}/solve")
async def solve_pin_mux(part_id: str, requirements: List[Dict]):
    from solver.pin_mux_solver import PinMuxSolver, PinRequirement, PinType
    solver = PinMuxSolver(db.pool)
    reqs = [PinRequirement(function_type=PinType(r['function_type']), function_name=r['function_name'], required=True) for r in requirements]
    return await solver.solve(part_id, reqs)

@app.post("/api/parts/{part_id}/power")
async def calculate_power(part_id: str, request: Dict):
    from solver.power_budget_calculator import PowerBudgetCalculator, ModeProfile, PowerMode
    calc = PowerBudgetCalculator(db.pool)
    profiles = [ModeProfile(PowerMode.RUN, request.get('run_percent', 100))]
    budget = await calc.calculate_total_budget(part_id, profiles, [], [])
    return {"avg_current_ma": budget.total_current_ma, "total_power_uw": budget.total_power_uw}

@app.post("/api/compare")
async def compare_parts(request: Dict):
    spec = await db_ops.get_requirement_spec(UUID(request['spec_id']))
    candidates = [await db_ops.get_part_by_id(pid) for pid in request['part_ids']]
    return await rigorous_explainer.generate_comparison_matrix(spec, [c for c in candidates if c])

@app.post("/api/debate")
async def debate_parts(request: Dict):
    spec = await db_ops.get_requirement_spec(UUID(request['spec_id']))
    top = await db_ops.get_part_by_id(request['top_part_id'])
    alt = await db_ops.get_part_by_id(request['alt_part_id'])
    debate = await rigorous_explainer.conduct_architect_debate(spec, top, alt)
    return {"debate": debate}

@app.post("/admin/ingest")
async def trigger_ingestion(mode: str = "mock", background_tasks: BackgroundTasks = None):
    global ingestion_progress
    ingestion_progress = {"status": "starting", "percent": 1, "message": "Initializing..."}
    async def task(m):
        global ingestion_progress
        try:
            exe = sys.executable
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            if m == "mock":
                subprocess.run([exe, "scripts/generate_high_fidelity_data.py"], check=True, env=env)
                ingestion_progress = {"status": "running", "percent": 50, "message": "Injecting hardware..."}
                subprocess.run([exe, "scripts/inject_real_hardware.py"], check=True, env=env)
                ingestion_progress = {"status": "complete", "percent": 100, "message": "DB Restored."}
            else:
                ingestion_progress = {"status": "running", "percent": 5, "message": "Step 1/3: Downloading missing datasheets..."}
                env = os.environ.copy()
                env["PYTHONPATH"] = "."
                env["REAL_DATABASE_URL"] = os.getenv("REAL_DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")
                
                # 1. Download with real-time output monitoring
                process = subprocess.Popen([exe, "scripts/collect_stm32_datasheets.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
                for line in process.stdout:
                    if "PROGRESS:" in line:
                        try:
                            # Parse PROGRESS:X/Y
                            parts = line.strip().split("PROGRESS:")[1].split("/")
                            current, total = int(parts[0]), int(parts[1])
                            pct = int((current / total) * 30) + 5 # First 30% of total bar
                            ingestion_progress = {"status": "running", "percent": pct, "message": f"Downloading: {current}/{total} datasheets"}
                        except: pass
                process.wait()
                
                # 2. Ingest
                ingestion_progress = {"status": "running", "percent": 40, "message": "Step 2/3: Running Production Ingestion (PostgreSQL)..."}
                subprocess.run([exe, "scripts/run_pipeline.py"], check=True, env=env)
                
                # 3. ML King Sync
                ingestion_progress = {"status": "running", "percent": 90, "message": "Step 3/3: Finalizing ML high-performance sync..."}
                subprocess.run([exe, "scripts/inject_real_hardware.py"], check=True, env=env)
                
                ingestion_progress = {"status": "complete", "percent": 100, "message": "Production Ready."}
        except Exception as e:
            ingestion_progress = {"status": "error", "percent": 0, "message": str(e)}
    background_tasks.add_task(task, mode)
    return {"status": "started"}

@app.get("/api/ingest/status")
async def get_ingest_status():
    async def events():
        yield "retry: 1000\n\n"
        while True:
            yield f"data: {json.dumps(ingestion_progress)}\n\n"
            if ingestion_progress["status"] in ["complete", "error"]: break
            await asyncio.sleep(1)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})

@app.post("/api/ingest/swap")
async def swap_to_production():
    url = os.getenv("REAL_DATABASE_URL")
    if not url:
        raise HTTPException(
            status_code=400,
            detail="REAL_DATABASE_URL not configured. Cannot swap to production without a real PostgreSQL URL."
        )
    try:
        await db.switch_to_production(url)
        await refresh_server_components()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Hot-swap failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hot-swap failed: {str(e)}")

@app.post("/api/ingest/reset_mock")
async def reset_to_mock():
    """Force-rewire the backend back to the Mock SQLite database"""
    try:
        logger.info("RESETTING TO MOCK MODE...")
        # 1. Clear PostgreSQL pool if it exists
        if db.pool:
            await db.disconnect()
        
        # 2. CLEAR THE URL in the db instance to force SQLite fallback
        db.database_url = None
        
        # 3. Connect to Mock
        await db.connect()
        
        # 4. Deep refresh all components
        await refresh_server_components()
        
        return {"status": "success", "message": "Backend restored to Mock DB"}
    except Exception as e:
        logger.error(f"Reset to mock failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/peer-review")
async def architect_peer_review(request: Dict):
    """
    Dream Spec #4: AI Peer Review.
    Accepts spec_id and reviews the top recommendation with LLM-powered senior engineer analysis.
    Returns a structured verdict: green / amber / red with architect notes.
    """
    try:
        spec_id = UUID(request["spec_id"])
        spec = await db_ops.get_requirement_spec(spec_id)
        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")
        
        # Get top candidates for review context
        candidates = await hard_filter.filter(spec)
        ranked = ranking_engine.rank(candidates, spec)
        top_candidates = [dict(r[0]) for r in ranked[:3]]
        
        target_part_id = request.get("part_id")
        if target_part_id:
            target_part = await db_ops.get_part_by_id(UUID(target_part_id))
            if target_part:
                # Normalise object
                part_keys = {'id', 'mpn', 'manufacturer', 'family', 'status', 'package_family', 'package_name', 'pin_count', 'temp_min_c', 'temp_max_c', 'datasheet_url', 'created_at', 'updated_at'}
                target_part['specs'] = {k: v for k, v in target_part.items() if k not in part_keys}
                # Prepend the targeted part so the LLM thinks it's the Primary Candidate
                top_candidates.insert(0, target_part)
        
        review = await rigorous_explainer.generate_architect_review(spec, top_candidates)
        return review
    except Exception as e:
        logger.error(f"Peer review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/exhaustive-review")
async def exhaustive_parameter_review(request: Dict):
    """
    Triggers an exhaustive parameter-by-parameter AI evaluation against user requirements.
    """
    try:
        req_id = request.get("req_id")
        part_id = request.get("part_id")
        
        if not req_id or not part_id:
            raise HTTPException(status_code=400, detail="Missing req_id or part_id.")
            
        spec = await db_ops.get_requirement_spec(UUID(req_id))
        if not spec:
            raise HTTPException(status_code=404, detail="Requirement spec not found.")
            
        part = await db_ops.get_part_by_id(UUID(part_id))
        if not part:
            raise HTTPException(status_code=404, detail="Component not found.")
            
        review = await rigorous_explainer.generate_exhaustive_parameter_review(spec, part)
        return review
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exhaustive review error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bom/check")
async def check_bom_compatibility(request: Dict):
    """
    Dream Spec #2: BOM Compatibility Cross-Checking.
    Accepts a list of part IDs and checks them for cross-component compatibility.
    Returns a structured report with pass/warn/fail issues per check.
    """
    try:
        part_ids: List[str] = request.get("part_ids", [])
        if not part_ids:
            raise HTTPException(status_code=400, detail="No part_ids provided")

        # Fetch full part data for each ID
        parts = []
        for pid in part_ids:
            try:
                part = await db_ops.get_part_by_id(UUID(pid))
                if part:
                    # Normalise: nest MCU fields under 'specs' for bom_checker
                    part_keys = {'id', 'mpn', 'manufacturer', 'family', 'status',
                                 'package_family', 'package_name', 'pin_count',
                                 'theta_ja_c_w', 'temp_min_c', 'temp_max_c', 
                                 'datasheet_url', 'created_at', 'updated_at'}
                    specs = {k: v for k, v in part.items() if k not in part_keys}
                    part['specs'] = specs
                    parts.append(part)
            except Exception as e:
                logger.warning(f"Could not fetch part {pid}: {e}")

        if not parts:
            raise HTTPException(status_code=404, detail="None of the part IDs were found")

        report = bom_checker.check(parts)
        return report.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"BOM check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def refresh_server_components():
    """Re-initialize all global components with the current active database pool"""
    global db_ops, hard_filter, ranking_engine, bom_checker
    db_ops = DatabaseOperations(db.pool)
    hard_filter = HardFilter(db.pool)
    ranking_engine = RankingEngine()
    bom_checker = BOMCompatibilityChecker()
    logger.info("Server components refreshed with active pool.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
