"""Core package initialization"""

from .models import (
    # Enums
    SourceType,
    PartStatus,
    ConflictStatus,
    QuestionTier,
    OptimizationGoal,
    
    # Evidence & Provenance
    EvidenceRecord,
    DocumentRecord,
    
    # Requirements
    RequirementSpec,
    
    # Questions & Answers
    Question,
    Answer,
    QuestionBatch,
    
    # Parts & Specs
    PartBase,
    MCUSpecBase,
    CandidatePart,
    NearMissSuggestion,
    
    # Recommendations
    RecommendationResult,
    
    # Conflicts
    Conflict,
    
    # Ingestion
    ExtractionRun,
    IngestionRequest,
    
    # Templates
    SubsystemDefinition,
    MappingRule,
    DesignTemplate,
    
    # API Models
    ParseRequirementsRequest,
    ParseRequirementsResponse,
    AnswerQuestionsRequest,
    AnswerQuestionsResponse,
    RecommendRequest,
)

__all__ = [
    # Enums
    "SourceType",
    "PartStatus",
    "ConflictStatus",
    "QuestionTier",
    "OptimizationGoal",
    
    # Evidence & Provenance
    "EvidenceRecord",
    "DocumentRecord",
    
    # Requirements
    "RequirementSpec",
    
    # Questions & Answers
    "Question",
    "Answer",
    "QuestionBatch",
    
    # Parts & Specs
    "PartBase",
    "MCUSpecBase",
    "CandidatePart",
    "NearMissSuggestion",
    
    # Recommendations
    "RecommendationResult",
    
    # Conflicts
    "Conflict",
    
    # Ingestion
    "ExtractionRun",
    "IngestionRequest",
    
    # Templates
    "SubsystemDefinition",
    "MappingRule",
    "DesignTemplate",
    
    # API Models
    "ParseRequirementsRequest",
    "ParseRequirementsResponse",
    "AnswerQuestionsRequest",
    "AnswerQuestionsResponse",
    "RecommendRequest",
]
