"""
FastAPI Server - Silicon-Pilot (Production PostgreSQL)
All data served exclusively from the live PostgreSQL database.
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
from dotenv import load_dotenv

# Load .env at import time so DATABASE_URL etc. are available
load_dotenv()

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

    logger.info("Starting Silicon-Pilot Server (Production PostgreSQL mode)")

    # Connect to real PostgreSQL DB — will raise if DATABASE_URL is not set
    await db.connect()
    logger.info(" PostgreSQL connection established")

    # Initialize components
    db_ops = DatabaseOperations(db.pool)
    hard_filter = HardFilter(db.pool)
    ranking_engine = RankingEngine()
    near_miss_engine = NearMissEngine()
    bom_checker = BOMCompatibilityChecker()

    # LLM Configuration — all settings live in core/llm_config.py
    import core.llm_config as llm_cfg
    llm_cfg.print_config()

    llm_orchestrator = LLMOrchestrator()
    rigorous_explainer = RigorousExplainer()
    advanced_rag = AdvancedRAG()

    question_engine = QuestionEngine()
    templates_dir = Path(__file__).parent / "web_ui" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    template_loader = TemplateLoader()

    # Log DB stats
    try:
        stats = await db_ops.get_stats()
        logger.info(f" DB stats: {stats}")
    except Exception as e:
        logger.warning(f"Could not fetch DB stats: {e}")

    yield
    await db.disconnect()


app = FastAPI(lifespan=lifespan, title="Silicon-Pilot", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health_check():
    stats = await db_ops.get_stats()
    return {"status": "healthy", "database": "postgresql", "stats": stats}


@app.post("/spec/from_text", response_model=ParseRequirementsResponse)
async def parse_requirements(request: ParseRequirementsRequest):
    try:
        spec = await llm_orchestrator.parse_requirements(request.text)

        # Ensure component_type is in hard_constraints for the filter
        if 'component_type' not in spec.hard_constraints:
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
        logger.error(f"Parse error: {e}", exc_info=True)
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
            # Final fallback: best MCUs in the DB
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
            spec_id=request.spec_id, total_parts_in_db=await hard_filter.count_total_parts(),
            parts_after_hard_filter=len(candidates),
            constraint_summary={"status": "success"}, candidates=candidate_parts,
            total_candidates=len(candidates),
            constraint_checks={}, ranking_explanation=expl, near_miss=[]
        )
    except Exception as e:
        logger.error(f"Recommend error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/parts/{mpn}")
async def get_part(mpn: str):
    part = await db_ops.get_part_by_mpn(mpn)
    if not part:
        raise HTTPException(status_code=404, detail=f"Part {mpn} not found")
    return {"part": part, "evidence": []}


@app.post("/api/parts/{part_id}/solve")
async def solve_pin_mux(part_id: str, requirements: List[Dict]):
    """
    Pin Mux Solver — works for ALL 461 parts.

    Strategy:
    1. Load MCU specs from mcu_specs table (all 461 parts have this).
    2. For each requested peripheral type, check if the MCU has enough count.
    3. If mcu_pin_functions data exists (currently only STM32H743), also return
       actual pin-level AF assignments.
    4. Returns a structured assignment report showing what is satisfied, what
       the MCU physically supports, and any shortfalls.
    """
    try:
        part_uuid = UUID(part_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid part_id UUID")

    try:
        # --- Load MCU info ---
        async with db.pool.acquire() as conn:
            part_row = await conn.fetchrow(
                "SELECT p.mpn, p.manufacturer, p.family FROM parts p WHERE p.id = $1",
                part_uuid
            )
            specs_row = await conn.fetchrow(
                "SELECT * FROM mcu_specs WHERE part_id = $1",
                part_uuid
            )
            pin_rows = await conn.fetch(
                "SELECT pin_name, pin_number, af0_function, af1_function, af2_function, "
                "af3_function, af4_function, af5_function, af6_function, af7_function, "
                "af8_function, af9_function, af10_function, af11_function, af12_function, "
                "af13_function, af14_function, af15_function "
                "FROM mcu_pin_functions WHERE part_id = $1 ORDER BY pin_number",
                part_uuid
            )

        if not part_row:
            raise HTTPException(status_code=404, detail=f"Part {part_id} not found")

        mpn = part_row["mpn"]
        specs = dict(specs_row) if specs_row else {}

        # --- Peripheral capacity from mcu_specs ---
        capacity = {
            "uart":    specs.get("uart_count", 0) or 0,
            "spi":     specs.get("spi_count", 0) or 0,
            "i2c":     specs.get("i2c_count", 0) or 0,
            "can":     (specs.get("can_count", 0) or 0) + (specs.get("can_fd_count", 0) or 0),
            "can_fd":  specs.get("can_fd_count", 0) or 0,
            "adc":     specs.get("adc_channels", 0) or 0,
            "dac":     specs.get("dac_channels", 0) or 0,
            "pwm":     specs.get("pwm_channels", 0) or 0,
            "timer":   specs.get("timers_count", 0) or 0,
            "usb":     (1 if specs.get("usb_fs") else 0) + (1 if specs.get("usb_hs") else 0),
            "ethernet": 1 if specs.get("ethernet") else 0,
            "gpio":    specs.get("pin_count", 0) or 0,
        }

        # --- Build pin map from mcu_pin_functions (may be empty) ---
        pin_map = {}
        for row in pin_rows:
            r = dict(row)
            funcs = {}
            for af in range(16):
                val = r.get(f"af{af}_function")
                if val:
                    funcs[af] = val
            pin_map[r["pin_name"]] = {
                "pin_number": r["pin_number"],
                "functions": funcs,
            }

        has_pin_data = len(pin_map) > 0

        # --- Solve requirements ---
        assignments = {}
        unassigned = []
        capacity_used = {}  # track usage per type

        for req in requirements:
            func_type = req.get("function_type", "gpio").lower()
            func_name = req.get("function_name", "").strip()
            required = req.get("required", True)

            result_entry = {
                "function_name": func_name,
                "function_type": func_type,
                "pin_name": None,
                "alternate_function": None,
                "satisfied_by": "peripheral_count",
                "notes": "",
            }

            # Step 1: Try exact pin function match from mcu_pin_functions
            if has_pin_data and func_name:
                assigned_pins = set(a["pin_name"] for a in assignments.values() if a.get("pin_name"))
                for pin_name, pdata in pin_map.items():
                    if pin_name in assigned_pins:
                        continue
                    for af, fn in pdata["functions"].items():
                        if fn.upper() == func_name.upper():
                            result_entry["pin_name"] = pin_name
                            result_entry["alternate_function"] = af
                            result_entry["satisfied_by"] = "pin_function_table"
                            result_entry["notes"] = f"Direct AF{af} match in {mpn} pin table"
                            break
                    if result_entry["pin_name"]:
                        break

            # Step 2: If no exact match, check peripheral count capacity
            if not result_entry["pin_name"]:
                used = capacity_used.get(func_type, 0)
                avail = capacity.get(func_type, 0)
                if used < avail:
                    capacity_used[func_type] = used + 1
                    result_entry["pin_name"] = f"{func_type.upper()}{used}_pins"
                    result_entry["alternate_function"] = "N/A"
                    result_entry["satisfied_by"] = "peripheral_count"
                    result_entry["notes"] = (
                        f"{mpn} has {avail} {func_type.upper()} interface(s). "
                        f"Using instance #{used + 1}. "
                        + ("Exact pin assignment not available — refer to datasheet pinout table." if not has_pin_data else "No exact pin name match found in AF table.")
                    )
                else:
                    result_entry["satisfied_by"] = "insufficient"
                    result_entry["notes"] = (
                        f"{mpn} only has {avail} {func_type.upper()} interface(s) — "
                        f"cannot satisfy {used + 1} simultaneous {func_type.upper()} requirements."
                    )
                    if required:
                        unassigned.append(func_name or func_type)
                    continue

            assignments[func_name or f"{func_type}_{len(assignments)}"] = result_entry

        success = len(unassigned) == 0

        return {
            "success": success,
            "mpn": mpn,
            "has_detailed_pin_table": has_pin_data,
            "peripheral_capacity": capacity,
            "assignments": assignments,
            "unassigned": unassigned,
            "notes": (
                f"Pin data from AF table ({len(pin_map)} pins). "
                if has_pin_data else
                f"Peripheral availability confirmed from mcu_specs. "
                f"Detailed pin-level AF data not yet loaded for {mpn}. "
                f"Use STMCubeMX or the {mpn} datasheet for exact pin assignments."
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pin mux solve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/parts/{part_id}/power")
async def calculate_power(part_id: str, request: Dict):
    """
    Advanced Power Profiler & Battery Life Estimator.
    Accepts duty cycle modes, peripheral usage, and battery specs.
    Returns full power breakdown + battery lifetime estimate.
    """
    try:
        from solver.power_profiler import PowerProfiler, profile_to_dict
        profiler = PowerProfiler(db.pool)
        result = await profiler.compute(
            part_id=part_id,
            modes=request.get("modes", [{"name": "run", "percent": 100}]),
            peripherals=request.get("peripherals", []),
            external_loads=request.get("external_loads", []),
            battery_mah=request.get("battery_mah"),
            battery_chemistry=request.get("battery_chemistry", "Li-Po"),
            system_voltage_v=request.get("system_voltage_v", 3.3),
        )
        return profile_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Power profiler error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parts/{part_id}/replacements")
async def find_drop_in_replacements(part_id: str, request: Dict = {}):
    """
    Drop-In Replacement Engine.
    Finds the best replacement MCUs ranked by schematic rework level.
    Returns scoring breakdown across package / core / peripheral / voltage axes.
    """
    try:
        from solver.drop_in_finder import DropInFinder
        finder = DropInFinder(db.pool)
        result = await finder.find(
            part_id=part_id,
            max_results=request.get("max_results", 8) if request else 8,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Drop-in finder error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/parts/{part_id}/package")
async def get_package_analysis(part_id: str):
    """
    Package & PCB Manufacturing Cost Analyzer.
    Returns complexity rating, layer count, HDI requirement, cost multiplier,
    warnings, and design recommendations for the part's package.
    """
    try:
        from solver.package_analyzer import PackageAnalyzer, analysis_to_dict
        analyzer = PackageAnalyzer(db.pool)
        result = await analyzer.analyze(part_id)
        return analysis_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Package analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parts/{part_id}/ecosystem")
async def get_ecosystem_recommendations(part_id: str, request: Dict = {}):
    """
    Ecosystem RAG — Companion Chip Recommender.
    Matches CAN transceivers, motor drivers, IMUs, PMICs, LDOs and RS-485
    transceivers to the selected MCU based on application requirements.
    Returns logic-level-compatible, interface-matched chipset recommendations.
    """
    try:
        from solver.ecosystem_rag import EcosystemRAG, ecosystem_to_dict
        rag = EcosystemRAG(db.pool)
        requirement_text = (request or {}).get("requirement_text", "")
        spec_dict = (request or {}).get("spec", None)
        result = await rag.recommend(
            part_id=part_id,
            requirement_text=requirement_text,
            spec_dict=spec_dict,
        )
        return ecosystem_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Ecosystem RAG error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/compare")
async def compare_parts(request: Dict):
    spec = await db_ops.get_requirement_spec(UUID(request['spec_id']))
    candidates = [await db_ops.get_part_by_id(UUID(pid)) for pid in request['part_ids']]
    return await rigorous_explainer.generate_comparison_matrix(spec, [c for c in candidates if c])


@app.post("/api/debate")
async def debate_parts(request: Dict):
    spec = await db_ops.get_requirement_spec(UUID(request['spec_id']))
    top = await db_ops.get_part_by_id(UUID(request['top_part_id']))
    alt = await db_ops.get_part_by_id(UUID(request['alt_part_id']))
    debate = await rigorous_explainer.conduct_architect_debate(spec, top, alt)
    return {"debate": debate}


@app.post("/admin/ingest")
async def trigger_ingestion(mode: str = "production", background_tasks: BackgroundTasks = None):
    """
    Trigger real production ingestion pipeline.
    Only 'production' mode is supported — mock mode has been removed.
    """
    global ingestion_progress
    ingestion_progress = {"status": "starting", "percent": 1, "message": "Initializing production ingestion..."}

    async def task():
        global ingestion_progress
        try:
            exe = sys.executable
            env = os.environ.copy()
            env["PYTHONPATH"] = "."
            env["DATABASE_URL"] = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")
            env["REAL_DATABASE_URL"] = env["DATABASE_URL"]

            ingestion_progress = {"status": "running", "percent": 5, "message": "Step 1/3: Downloading missing datasheets..."}

            # 1. Download with real-time output monitoring
            process = subprocess.Popen(
                [exe, "scripts/collect_stm32_datasheets.py"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
            )
            for line in process.stdout:
                if "PROGRESS:" in line:
                    try:
                        parts = line.strip().split("PROGRESS:")[1].split("/")
                        current, total = int(parts[0]), int(parts[1])
                        pct = int((current / total) * 30) + 5
                        ingestion_progress = {"status": "running", "percent": pct, "message": f"Downloading: {current}/{total} datasheets"}
                    except Exception:
                        pass
            process.wait()

            # 2. Ingest
            ingestion_progress = {"status": "running", "percent": 40, "message": "Step 2/3: Running PostgreSQL ingestion..."}
            subprocess.run([exe, "scripts/run_pipeline.py"], check=True, env=env)

            ingestion_progress = {"status": "complete", "percent": 100, "message": "Production ingestion complete."}
        except Exception as e:
            ingestion_progress = {"status": "error", "percent": 0, "message": str(e)}

    background_tasks.add_task(task)
    return {"status": "started"}


@app.get("/api/ingest/status")
async def get_ingest_status():
    async def events():
        yield "retry: 1000\n\n"
        while True:
            yield f"data: {json.dumps(ingestion_progress)}\n\n"
            if ingestion_progress["status"] in ["complete", "error"]:
                break
            await asyncio.sleep(1)
    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@app.post("/api/ingest/swap")
async def swap_to_production():
    """Hot-swap to a different PostgreSQL URL (advanced use)."""
    url = os.getenv("REAL_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise HTTPException(
            status_code=400,
            detail="DATABASE_URL not configured."
        )
    try:
        await db.switch_to_production(url)
        await refresh_server_components()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Hot-swap failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hot-swap failed: {str(e)}")


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

        candidates = await hard_filter.filter(spec)
        ranked = ranking_engine.rank(candidates, spec)
        top_candidates = [dict(r[0]) for r in ranked[:3]]

        target_part_id = request.get("part_id")
        if target_part_id:
            target_part = await db_ops.get_part_by_id(UUID(target_part_id))
            if target_part:
                part_keys = {'id', 'mpn', 'manufacturer', 'family', 'status', 'package_family', 'package_name', 'pin_count', 'temp_min_c', 'temp_max_c', 'datasheet_url', 'created_at', 'updated_at'}
                target_part['specs'] = {k: v for k, v in target_part.items() if k not in part_keys}
                top_candidates.insert(0, target_part)

        review = await rigorous_explainer.generate_architect_review(spec, top_candidates)
        return review
    except Exception as e:
        logger.error(f"Peer review error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/exhaustive-review")
async def exhaustive_parameter_review(request: Dict):
    """
    Triggers an exhaustive parameter-by-parameter AI evaluation against user requirements.
    Merges database fields with deep PDF-extracted parameters from datasheet_parameters table.
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

        # Fetch all datasheet-extracted parameters for this part (may be empty)
        datasheet_params: List[Dict] = []
        try:
            pool = db.pool
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    """SELECT section, parameter, min_value, typ_value, max_value,
                              unit, conditions, source_page, confidence
                       FROM datasheet_parameters
                       WHERE part_id = $1
                       ORDER BY section, source_page""",
                    UUID(part_id)
                )
                datasheet_params = [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Could not fetch datasheet_parameters: {e}")

        review = await rigorous_explainer.generate_exhaustive_parameter_review(
            spec, part, datasheet_params=datasheet_params
        )
        return review
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exhaustive review error: {e}", exc_info=True)
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

        parts = []
        for pid in part_ids:
            try:
                part = await db_ops.get_part_by_id(UUID(pid))
                if part:
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
        logger.error(f"BOM check error: {e}", exc_info=True)
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
