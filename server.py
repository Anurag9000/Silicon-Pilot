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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import asyncpg
from pathlib import Path

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

# web_ui imports
from templates.template_system import TemplateLoader
from llm.intent_classifier import IntentParser, TemplateMatcher
from architecture.compiler import ArchitectureBuilder, ConstraintCompiler
from architecture.enhanced_exports import ExportManager
from fastapi.templating import Jinja2Templates
from fastapi import Request

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

# web_ui globals
template_loader: Optional[TemplateLoader] = None
templates: Optional[Jinja2Templates] = None

# Background tasks
from fastapi import BackgroundTasks
import subprocess

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    global db_ops, hard_filter, ranking_engine, near_miss_engine, llm_orchestrator, question_engine
    
    # Startup
    logger.info("Starting HardwareGenius Unified Server")
    
    # Connect to database
    await db.connect()
    
    # Initialize components
    db_ops = DatabaseOperations(db.pool)
    hard_filter = HardFilter(db.pool)
    ranking_engine = RankingEngine()
    near_miss_engine = NearMissEngine()
    
    try:
        llm_orchestrator = LLMOrchestrator(
            api_key=os.getenv('OPENAI_API_KEY'),
        )
        logger.info("LLM Orchestrator initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM Orchestrator: {e}. LLM features will be disabled.")
        llm_orchestrator = None

    try:
        question_engine = QuestionEngine()
        logger.info("Question Engine initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Question Engine: {e}")
        question_engine = None
    
    # Initialize web_ui components
    global template_loader, templates
    templates_dir = Path(__file__).parent / "web_ui" / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    template_loader = TemplateLoader(str(templates_dir))
    
    logger.info("All components initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HardwareGenius API")
    await db.disconnect()


# Create FastAPI app
app = FastAPI(
    title="HardwareGenius API",
    description="Evidence-backed, deterministic hardware component recommendation system (Unified)",
    version="2.0.0",
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

# Mount Frontend Static Files
# This unifies the frontend serving into the main API server
static_dir = Path(__file__).parent / "web_ui" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ==================== Frontend Routes ====================

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the main frontend application"""
    # Use Jinja2 template if available, otherwise fallback
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
        
    index_path = Path(__file__).parent / "web_ui" / "templates" / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)

# ==================== Web UI API ====================

@app.post("/api/parse-intent")
async def parse_intent(request: Request):
    """Parse user intent"""
    data = await request.json()
    user_input = data.get("input", "")
    
    parser = IntentParser(use_llm=False)
    intent = parser.parse_intent(user_input)
    
    matcher = TemplateMatcher(template_loader)
    matches = matcher.match_templates(intent)
    
    return {
        "intent": {
            "device_type": intent.device_type,
            "keywords": intent.keywords,
            "extracted_params": intent.extracted_params
        },
        "matches": [
            {
                "template_id": m.template_id,
                "confidence": m.confidence,
                "match_reason": m.match_reason
            }
            for m in matches[:5]
        ]
    }


@app.get("/api/templates")
async def list_templates():
    """List all available templates"""
    templates_list = template_loader.list_all_templates()
    
    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "device_type": t.device_type,
                "description": t.description,
                "tags": t.tags
            }
            for t in templates_list
        ]
    }


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    """Get template details"""
    template = template_loader.load_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "device_type": template.device_type,
        "subsystems": list(template.subsystems.keys()),
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "type": q.type,
                "choices": q.choices if hasattr(q, 'choices') else None,
                "default": q.default if hasattr(q, 'default') else None,
                "priority": q.priority,
                "help_text": q.help_text if hasattr(q, 'help_text') else None
            }
            for q in template.questions
        ]
    }

@app.post("/api/build-architecture")
async def build_architecture(request: Request):
    """Build architecture from template and answers"""
    data = await request.json()
    template_id = data.get("template_id")
    answers = data.get("answers", {})
    
    template = template_loader.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    from architecture.compiler import build_architecture_from_template
    
    architecture = build_architecture_from_template(template, answers)
    
    compiler = ConstraintCompiler()
    # req_spec = compiler.compile_constraints(architecture) # unused in frontend for now
    
    # Simulate component recommendations
    bom = [
        {
            "category": "MCU",
            "manufacturer": "STMicroelectronics",
            "mpn": "STM32F405RGT6",
            "description": "ARM Cortex-M4, 168MHz, 1MB Flash",
            "quantity": 1,
            "price_usd": 5.50
        }
    ]
    
    return {
        "architecture": {
            "subsystems": list(architecture.subsystems.keys()),
            "subsystem_details": {
                name: {
                    "functions": list(subsys.functions),
                    "constraints": subsys.constraints
                }
                for name, subsys in architecture.subsystems.items()
            }
        },
        "bom": bom,
        "total_cost": sum(item["price_usd"] * item["quantity"] for item in bom)
    }


@app.post("/api/export")
async def export_design(request: Request):
    """Export design to various formats"""
    data = await request.json()
    format_type = data.get("format", "pdf")
    bom = data.get("bom", [])
    config = data.get("config", {})
    project_name = data.get("project_name", "design")
    
    export_manager = ExportManager()
    output_dir = Path(__file__).parent / "exports"
    output_dir.mkdir(exist_ok=True)
    
    try:
        if format_type == "eagle":
            content = export_manager.eagle.export(bom, project_name)
            filename = f"{project_name}_eagle.xml"
        elif format_type == "kicad":
            content = export_manager.kicad.export(bom)
            filename = f"{project_name}_kicad.csv"
        elif format_type == "altium":
            content = export_manager.altium.export(bom)
            filename = f"{project_name}_altium.csv"
        elif format_type == "pdf":
            content = export_manager.pdf.export(bom, config, project_name)
            filename = f"{project_name}_report.pdf"
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
        
        # Save file
        output_path = output_dir / filename
        if isinstance(content, bytes):
            output_path.write_bytes(content)
        else:
            output_path.write_text(content)
        
        return {
            "success": True,
            "filename": filename,
            "download_url": f"/downloads/{filename}"
        }
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/downloads/{filename}")
async def download_file(filename: str):
    """Download exported file"""
    file_path = Path(__file__).parent / "exports" / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)

# Helper for Pydantic models
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: Optional[str] = None
    flash_min_kb: Optional[int] = None
    flash_max_kb: Optional[int] = None
    ram_min_kb: Optional[int] = None
    freq_min_mhz: Optional[int] = None
    io_count_min: Optional[int] = None
    limit: int = 20

@app.post("/api/search")
async def search_parts(request: SearchRequest):
    """
    Faceted search for all component types (MCU, LDO, PMIC, etc).
    """
    if not db.pool:
        raise HTTPException(status_code=503, detail="Database not initialized")
        
    async with db.pool.acquire() as conn:
        # 1. Base Query on Parts
        # We use COALESCE/JSON construction to handle polymorphic specs
        query = """
            SELECT p.id, p.mpn, p.manufacturer, p.family, p.datasheet_url, p.package_family,
                   m.core, m.max_mhz, m.flash_kb, m.sram_kb,
                   l.vin_min_v as ldo_vin_min, l.vout_fixed_v as ldo_vout, l.iout_max_ma as ldo_iout,
                   pm.buck_count, pm.ldo_count,
                   c.data_rate_mbps as can_rate,
                   s.sensor_type, s.interface as sensor_interface,
                   psv.type as passive_type, psv.value_primary, psv.package_case
            FROM parts p
            LEFT JOIN mcu_specs m ON p.id = m.part_id
            LEFT JOIN ldo_specs l ON p.id = l.part_id
            LEFT JOIN pmic_specs pm ON p.id = pm.part_id
            LEFT JOIN can_specs c ON p.id = c.part_id
            LEFT JOIN sensor_specs s ON p.id = s.part_id
            LEFT JOIN passive_specs psv ON p.id = psv.part_id
            WHERE 1=1
        """
        params = []
        param_idx = 1
        
        # 2. Text Search
        if request.query:
            query += f" AND (p.mpn ILIKE ${param_idx} OR p.family ILIKE ${param_idx})"
            params.append(f"%{request.query}%")
            param_idx += 1
            
        # 3. MCU Specific Filters (Only apply if params provided)
        if request.flash_min_kb:
            query += f" AND m.flash_kb >= ${param_idx}"
            params.append(request.flash_min_kb)
            param_idx += 1
            
        if request.flash_max_kb:
            query += f" AND m.flash_kb <= ${param_idx}"
            params.append(request.flash_max_kb)
            param_idx += 1

        if request.ram_min_kb:
            query += f" AND m.sram_kb >= ${param_idx}"
            params.append(request.ram_min_kb)
            param_idx += 1
            
        if request.freq_min_mhz:
            query += f" AND m.max_mhz >= ${param_idx}"
            params.append(request.freq_min_mhz)
            param_idx += 1
            
        if request.io_count_min:
            query += f" AND (m.uart_count + m.spi_count + m.i2c_count + m.adc_count) >= ${param_idx}"
            params.append(request.io_count_min)
            param_idx += 1
            
        # Limit
        query += f" ORDER BY p.mpn ASC LIMIT ${param_idx}"
        params.append(request.limit)
        
        rows = await conn.fetch(query, *params)
        
        results = []
        for row in rows:
            r = dict(row)
            # Normalize specs into a clean dict for UI
            specs = {}
            if r.get('core'): # MCU
                specs = {k: r[k] for k in ['core', 'max_mhz', 'flash_kb', 'sram_kb'] if r.get(k) is not None}
                specs['type_label'] = 'MCU'
            elif r.get('ldo_vout'): # LDO
                specs = {k: r[k] for k in ['ldo_vin_min', 'ldo_vout', 'ldo_iout'] if r.get(k) is not None}
                specs['type_label'] = 'LDO'
            elif r.get('buck_count') is not None: # PMIC
                specs = {k: r[k] for k in ['buck_count', 'ldo_count'] if r.get(k) is not None}
                specs['type_label'] = 'PMIC'
            elif r.get('can_rate'): # CAN
                specs = {'data_rate': r['can_rate']}
                specs['type_label'] = 'CAN'
            elif r.get('sensor_type'): # Sensor
                specs = {'type': r['sensor_type'], 'interface': r['sensor_interface']}
                specs['type_label'] = 'Sensor'
            elif r.get('passive_type'): # Passive
                specs = {'type': r['passive_type'], 'value': r['value_primary'], 'case': r['package_case']}
                specs['type_label'] = 'Passive'
            else:
                specs['type_label'] = 'Component'
                
            # Clean up top level
            entry = {
                "id": str(r['id']),
                "mpn": r['mpn'],
                "manufacturer": r['manufacturer'],
                "family": r['family'],
                "datasheet_url": r['datasheet_url'],
                "type_label": specs['type_label'],
                "specs": specs
            }
            results.append(entry)
            
        return {"count": len(results), "results": results}


# ==================== Pin Mux Solver ====================

@app.get("/api/parts/{part_id}/pins")
async def get_part_pins(part_id: str):
    """Get pin definitions for a part"""
    try:
        from solver.pin_mux_solver import PinMuxSolver
        if not db.pool:
             raise HTTPException(status_code=503, detail="Database not initialized")
        solver = PinMuxSolver(db.pool)
        pins = await solver.get_pin_functions(part_id)
        return pins
    except Exception as e:
        logger.error(f"Error fetching pins: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

class PinRequirementRequest(BaseModel):
    function_type: str
    function_name: str
    required: bool = True

@app.post("/api/parts/{part_id}/solve")
async def solve_pin_mux(part_id: str, requirements: List[PinRequirementRequest]):
    """Solve pin muxing for a part"""
    try:
        from solver.pin_mux_solver import PinMuxSolver, PinRequirement, PinType
        if not db.pool:
             raise HTTPException(status_code=503, detail="Database not initialized")
        solver = PinMuxSolver(db.pool)
        
        # Convert request to internal model
        reqs = []
        for r in requirements:
            reqs.append(PinRequirement(
                function_type=PinType(r.function_type),
                function_name=r.function_name,
                required=r.required
            ))
            
        result = await solver.solve(part_id, reqs)
        return result
    except Exception as e:
        logger.error(f"Error solving pin mux: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Power Budget Calculator ====================

class PowerRequest(BaseModel):
    run_percent: float = 10.0
    sleep_percent: float = 80.0
    stop_percent: float = 10.0
    peripherals: List[str] = [] # list of names like "USART1"
    
@app.post("/api/parts/{part_id}/power")
async def calculate_power(part_id: str, request: PowerRequest):
    """Calculate power budget"""
    try:
        from solver.power_budget_calculator import PowerBudgetCalculator, ModeProfile, PowerMode
        # Basic mapping for MVP
        if not db.pool:
             raise HTTPException(status_code=503, detail="Database not initialized")
        calc = PowerBudgetCalculator(db.pool)
        
        profiles = [
            ModeProfile(PowerMode.RUN, request.run_percent),
            ModeProfile(PowerMode.SLEEP, request.sleep_percent),
            ModeProfile(PowerMode.STOP, request.stop_percent)
        ]
        
        # Simplified: Peripherals and External handling omitted for MVP speed
        # But this connects the pipes
        budget = await calc.calculate_total_budget(part_id, profiles, [], [])
        
        return {
            "total_power_uw": budget.total_power_uw,
            "avg_current_ma": budget.total_current_ma,
            "breakdown": budget.breakdown
        }
    except Exception as e:
        logger.error(f"Error calculating power: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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



# ==================== Ingestion Control ====================

@app.post("/admin/ingest")
async def trigger_ingestion(background_tasks: BackgroundTasks):
    """Trigger the STM32 ingestion process in the background"""
    def run_ingestion():
        logger.info("Starting ingestion process...")
        try:
            # Run the ingestion script as a subprocess to avoid blocking the event loop
            # and to handle the large memory usage of PDF processing
            script_path = "scripts/run_pipeline.py"
            subprocess.run(["python", script_path], check=True)
            logger.info("Ingestion process completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"Ingestion process failed: {e}")
        except Exception as e:
            logger.error(f"Ingestion trigger error: {e}")

    background_tasks.add_task(run_ingestion)
    return {"status": "Ingestion triggered", "message": "Check server logs for progress"}


# ==================== Evidence Content ====================

@app.get("/evidence/{evidence_id}/content")
async def get_evidence_content(evidence_id: UUID):
    """Get the actual image content for an evidence record"""
    try:
        evidence = await db_ops.get_evidence_by_id(evidence_id)
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")
        
        # In a real system, this would fetch from S3 or local storage
        # using evidence.snippet_storage_key
        # For MVP, we'll look for a local file if keys are paths
        
        # Placeholder: Return a generic image or fail gracefully if not implemented
        # Check if we have a valid path in storage_key
        key = evidence.get("snippet_storage_key")
        if key and os.path.exists(key):
             return FileResponse(key)
        
        # Fallback/Mock
        return JSONResponse(
            content={"message": "Evidence content not available in storage", "key": key},
            status_code=404
        )
    
    except Exception as e:
        logger.error(f"Error serving evidence content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Serve on 8000
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
