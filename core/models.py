"""
Core Data Models for HardwareGenius

Pydantic models for API contracts, validation, and internal data structures.
These models enforce the "evidence-required" principle and deterministic behavior.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from datetime import datetime
from uuid import UUID


# ============================================================================
# ENUMS
# ============================================================================

class SourceType(str, Enum):
    """Document source types"""
    MFG_PDF = "mfg_pdf"
    MFG_HTML = "mfg_html"
    DIST_HTML = "dist_html"
    OTHER = "other"


class PartStatus(str, Enum):
    """Part lifecycle status"""
    ACTIVE = "active"
    NRND = "nrnd"  # Not Recommended for New Designs
    EOL = "eol"    # End of Life
    UNKNOWN = "unknown"


class ConflictStatus(str, Enum):
    """Conflict resolution status"""
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class QuestionTier(int, Enum):
    """Question priority tiers"""
    TIER_1 = 1  # Mandatory - must answer to get valid recommendations
    TIER_2 = 2  # Optimization - improves ranking
    TIER_3 = 3  # Future-proofing - optional


class OptimizationGoal(str, Enum):
    """Multi-criteria optimization goals"""
    COST = "cost"
    POWER = "power"
    PERFORMANCE = "performance"
    BALANCED = "balanced"


# ============================================================================
# EVIDENCE & PROVENANCE
# ============================================================================

class EvidenceRecord(BaseModel):
    """
    Evidence record for a single extracted field.
    CRITICAL: Every spec field used in decisions must have evidence.
    """
    id: Optional[UUID] = None
    part_id: UUID
    field_path: str  # e.g., "mcu_specs.flash_kb"
    
    # Extraction
    extracted_value_raw: str
    normalized_value: Dict[str, Any]  # {"value": 2048, "unit": "kb"}
    
    # Source
    document_id: UUID
    page: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None  # {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    snippet_storage_key: Optional[str] = None  # S3 key for snippet image
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0)
    parser_version: str
    
    extracted_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentRecord(BaseModel):
    """Document source tracking"""
    id: Optional[UUID] = None
    source_url: str
    source_type: SourceType
    doc_hash: str  # SHA-256
    content_type: str
    storage_key: str  # S3 key
    version: int = 1
    fetched_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# REQUIREMENT SPECIFICATION
# ============================================================================

class RequirementSpec(BaseModel):
    """
    Canonical internal format for user requirements.
    All user input compiles into this structure.
    """
    id: Optional[UUID] = None
    
    # Hard constraints (MUST satisfy)
    hard_constraints: Dict[str, Any] = Field(default_factory=dict)
    
    # Soft preferences (NICE to have, used for ranking)
    soft_constraints: Dict[str, Any] = Field(default_factory=dict)
    
    # Environment & production constraints
    environment: Dict[str, Any] = Field(default_factory=dict)  # temp, EMC, certifications
    production: Dict[str, Any] = Field(default_factory=dict)   # availability, cost ceiling, lifecycle
    
    # Interfaces & peripherals
    interfaces: Dict[str, int] = Field(default_factory=dict)  # {"can": 2, "uart": 2, ...}
    
    # Power budget
    power_budget: Optional[Dict[str, Any]] = None
    
    # Performance targets
    performance: Optional[Dict[str, Any]] = None
    
    # Optimization goal
    optimization_goal: OptimizationGoal = OptimizationGoal.BALANCED
    
    # Uncertainty tracking
    unknowns: List[str] = Field(default_factory=list)  # Fields not yet specified
    assumptions: Dict[str, Any] = Field(default_factory=dict)  # Explicit assumed values
    
    # Metadata
    source_text: Optional[str] = None
    mode: str = "constraint"  # constraint or intent
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# QUESTION & ANSWER
# ============================================================================

class Question(BaseModel):
    """A single question to refine requirements"""
    id: Optional[UUID] = None
    field_name: str  # Which RequirementSpec field this affects
    question_text: str
    why_asking: str  # Explanation for user
    tier: QuestionTier
    options: Optional[List[str]] = None  # For multiple choice
    depends_on: Optional[UUID] = None  # Question dependency
    
    # Information gain metadata (for debugging)
    information_gain: Optional[float] = None


class Answer(BaseModel):
    """User's answer to a question"""
    question_id: UUID
    selected_value: Any
    confidence: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QuestionBatch(BaseModel):
    """Batch of questions for a single turn"""
    spec_id: UUID
    turn_index: int
    questions: List[Question]
    stop_reason: Optional[str] = None  # "tier_1_complete", "top_n_stable", "user_skip"


# ============================================================================
# PARTS & SPECIFICATIONS
# ============================================================================

class PartBase(BaseModel):
    """Base part information"""
    id: Optional[UUID] = None
    mpn: str
    manufacturer: str
    family: Optional[str] = None
    status: PartStatus = PartStatus.ACTIVE
    package_family: Optional[str] = None
    package_name: Optional[str] = None
    pin_count: Optional[int] = None
    temp_min_c: Optional[int] = None
    temp_max_c: Optional[int] = None


class MCUSpecBase(BaseModel):
    """MCU specifications (typed fields)"""
    part_id: UUID
    
    # Core
    core: Optional[str] = None
    max_mhz: Optional[int] = None
    flash_kb: Optional[int] = None
    sram_kb: Optional[int] = None
    eeprom_kb: Optional[int] = None
    
    # Peripherals
    can_count: int = 0
    can_fd_count: int = 0
    uart_count: int = 0
    spi_count: int = 0
    i2c_count: int = 0
    usb_fs: bool = False
    usb_hs: bool = False
    ethernet: bool = False
    adc_channels: int = 0
    dac_channels: int = 0
    timers_count: int = 0
    pwm_channels: int = 0
    
    # Features
    has_fpu: bool = False
    has_dsp: bool = False
    has_crypto: bool = False
    has_wireless: bool = False
    
    # Electrical
    vdd_min_v: Optional[float] = None
    vdd_max_v: Optional[float] = None
    
    # Power
    active_ma: Optional[float] = None
    standby_ua: Optional[float] = None
    sleep_ua: Optional[float] = None
    
    # Cost (volatile)
    cost_usd: Optional[float] = None
    
    # Extensibility
    extras: Optional[Dict[str, Any]] = None


class CandidatePart(BaseModel):
    """
    A candidate part with score breakdown and evidence pointers.
    Used in recommendation results.
    """
    part: PartBase
    specs: MCUSpecBase
    
    # Scoring
    total_score: float
    score_breakdown: Dict[str, float]  # {"headroom": 0.8, "ecosystem": 0.9, ...}
    
    # Constraint satisfaction
    satisfies_all_hard: bool
    failed_constraints: List[str] = Field(default_factory=list)
    
    # Evidence
    evidence_ids: List[UUID] = Field(default_factory=list)
    evidence_coverage: float = Field(ge=0.0, le=1.0)  # % of fields with evidence
    
    # Ranking
    rank: int


class NearMissSuggestion(BaseModel):
    """Near-miss candidate with relaxation suggestion"""
    part: PartBase
    specs: MCUSpecBase
    failed_constraint: str
    current_value: Any
    required_value: Any
    gap: str  # Human-readable gap description
    relaxation_suggestion: str


# ============================================================================
# RECOMMENDATION RESULT
# ============================================================================

class RecommendationResult(BaseModel):
    """
    Complete recommendation result with evidence and explanations.
    This is what the API returns to users.
    """
    spec_id: UUID
    
    # Candidates
    candidates: List[CandidatePart]
    
    # Constraint checks
    total_parts_in_db: int
    parts_after_hard_filter: int
    
    # Explanations
    constraint_summary: Dict[str, Any]  # Which constraints were applied
    ranking_explanation: str
    
    # Near-miss suggestions
    near_miss: List[NearMissSuggestion] = Field(default_factory=list)
    
    # Questions (if more refinement needed)
    suggested_questions: Optional[QuestionBatch] = None
    
    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: Optional[float] = None


# ============================================================================
# CONFLICT RESOLUTION
# ============================================================================

class Conflict(BaseModel):
    """Cross-source conflict requiring resolution"""
    id: Optional[UUID] = None
    part_id: UUID
    field_path: str
    evidence_ids: List[UUID]
    status: ConflictStatus = ConflictStatus.OPEN
    resolution: Optional[Dict[str, Any]] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# INGESTION PIPELINE
# ============================================================================

class ExtractionRun(BaseModel):
    """Track ingestion pipeline execution"""
    id: Optional[UUID] = None
    document_id: UUID
    parser_version: str
    status: str  # success, partial, failed
    error_message: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None  # {"fields_extracted": 15, ...}
    started_at: datetime
    completed_at: Optional[datetime] = None


class IngestionRequest(BaseModel):
    """Request to ingest a new document"""
    source_url: str
    source_type: SourceType
    priority: int = 5  # 1-10, higher = more urgent
    force_reprocess: bool = False  # Reprocess even if hash exists


# ============================================================================
# TEMPLATES (v2: Intent → Architecture)
# ============================================================================

class SubsystemDefinition(BaseModel):
    """Definition of a subsystem in a design template"""
    name: str
    description: str
    required_interfaces: List[str]
    constraints: Dict[str, Any]


class MappingRule(BaseModel):
    """Rule for mapping answers to constraints"""
    condition: str  # e.g., "motor_type == 'BLDC'"
    constraints: Dict[str, Any]


class DesignTemplate(BaseModel):
    """Template for intent → architecture"""
    id: Optional[UUID] = None
    name: str
    description: str
    subsystems: List[SubsystemDefinition]
    questions: List[Question]
    mapping_rules: List[MappingRule]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# API REQUEST/RESPONSE MODELS
# ============================================================================

class ParseRequirementsRequest(BaseModel):
    """Request to parse natural language into RequirementSpec"""
    text: str
    mode: str = "constraint"  # constraint or intent


class ParseRequirementsResponse(BaseModel):
    """Response with parsed spec and initial questions"""
    spec: RequirementSpec
    questions: Optional[QuestionBatch] = None


class AnswerQuestionsRequest(BaseModel):
    """Request to process user answers"""
    spec_id: UUID
    answers: List[Answer]


class AnswerQuestionsResponse(BaseModel):
    """Response with updated spec and next questions"""
    spec: RequirementSpec
    questions: Optional[QuestionBatch] = None
    ready_for_recommendation: bool


class RecommendRequest(BaseModel):
    """Request for recommendations"""
    spec_id: UUID
    max_results: int = 10
    include_near_miss: bool = True


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

# Note: Field validators are already defined inline using Pydantic's Field() constraints
# (e.g., Field(ge=0.0, le=1.0) for confidence fields)

