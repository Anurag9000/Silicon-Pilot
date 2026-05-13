"""
Template System for Silicon-Pilot Phase 2

Loads, validates, and manages device templates for architecture synthesis.
Templates are YAML files containing curated engineering knowledge.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml
from pydantic import BaseModel, Field, field_validator
from enum import Enum

from core.ontology import (
    DeviceType, SubsystemType, InterfaceType,
    EnvironmentType, TemperatureGrade, PowerProfile, PerformanceClass
)


# ============================================================================
# Template Schema Models
# ============================================================================

class QuestionType(str, Enum):
    """Question input types"""
    CHOICE = "choice"
    NUMBER = "number"
    RANGE = "range"
    BOOLEAN = "boolean"
    TEXT = "text"


class QuestionPriority(str, Enum):
    """Question priority levels"""
    HIGH = "high"      # Must answer
    MEDIUM = "medium"  # Should answer
    LOW = "low"        # Optional


class TemplateQuestion(BaseModel):
    """A question to ask the user during template instantiation"""
    id: str
    text: str
    type: "QuestionType"
    priority: "QuestionPriority" = QuestionPriority.MEDIUM
    choices: Optional[List[str]] = None
    default: Optional[Any] = None
    help_text: Optional[str] = None
    
    @field_validator('choices')
    @classmethod
    def validate_choices(cls, v, info):
        if info.data.get('type') == QuestionType.CHOICE and not v:
            raise ValueError("CHOICE questions must have choices")
        return v


TemplateQuestion.model_rebuild()

class RuleAction(BaseModel):
    """An action to execute when a rule condition is met"""
    type: str  # update_constraint, add_subsystem, remove_subsystem, etc.
    subsystem: Optional[str] = None
    field: Optional[str] = None
    operation: Optional[str] = None  # add, multiply, set, etc.
    value: Optional[Any] = None

TemplateQuestion.model_rebuild()
RuleAction.model_rebuild()


class TemplateRule(BaseModel):
    """Conditional rule that modifies the architecture based on answers"""
    condition: str  # Python expression, e.g., "motor_type == 'BLDC'"
    actions: List["RuleAction"]
    description: Optional[str] = None


TemplateRule.model_rebuild()

class SubsystemTemplate(BaseModel):
    """Template for a subsystem within a device"""
    required_functions: List[str] = Field(default_factory=list)
    baseline_constraints: Dict[str, Any] = Field(default_factory=dict)
    optional: bool = False
    notes: Optional[str] = None

SubsystemTemplate.model_rebuild()


class DeviceTemplate(BaseModel):
    """Complete device template"""
    id: str
    version: str = "1.0"
    device_type: DeviceType
    name: str
    
    @field_validator('device_type', mode='before')
    @classmethod
    def validate_device_type(cls, v):
        if isinstance(v, str):
            try:
                return DeviceType(v.lower())
            except ValueError:
                return v
        return v
    
    description: str
    
    # Architecture
    subsystems: Dict[str, "SubsystemTemplate"]
    required_interfaces: List[str] = Field(default_factory=list)
    
    # User interaction
    questions: List["TemplateQuestion"] = Field(default_factory=list)
    rules: List["TemplateRule"] = Field(default_factory=list)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # Documentation
    use_cases: List[str] = Field(default_factory=list)
    example_products: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)

TemplateRule.model_rebuild()
DeviceTemplate.model_rebuild()


# ============================================================================
# Template Loader
# ============================================================================

class TemplateLoader:
    """Loads and validates device templates from YAML files"""
    
    def __init__(self, template_dir: Path = Path("templates")):
        self.template_dir = Path(template_dir)
        self.templates: Dict[str, DeviceTemplate] = {}
        self._load_all_templates()
    
    def _load_all_templates(self):
        """Load all templates from the template directory"""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            return
        
        for yaml_file in self.template_dir.rglob("*.yaml"):
            try:
                template = self.load_template(yaml_file)
                self.templates[template.id] = template
            except Exception as e:
                try:
                    print(f"Warning: Failed to load template {yaml_file}: {e}")
                except UnicodeEncodeError:
                    print(f"Warning: Failed to load template {yaml_file.name}: [Unicode Error]")
    
    def load_template(self, template_path: Path) -> DeviceTemplate:
        """Load a single template from a YAML file"""
        with open(template_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Validate and parse
        template = DeviceTemplate(**data)
        return template
    
    def get_template(self, template_id: str) -> Optional[DeviceTemplate]:
        """Get a template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_type(self, device_type: DeviceType) -> List[DeviceTemplate]:
        """Get all templates for a specific device type"""
        return [
            t for t in self.templates.values()
            if t.device_type == device_type
        ]
    
    def get_templates_by_tags(self, tags: List[str]) -> List[DeviceTemplate]:
        """Get templates matching any of the given tags"""
        return [
            t for t in self.templates.values()
            if any(tag in t.tags for tag in tags)
        ]
    
    def search_templates(self, query: str) -> List[DeviceTemplate]:
        """Search templates by name, description, or tags"""
        query_lower = query.lower()
        results = []
        
        for template in self.templates.values():
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)
        
        return results
    
    def list_all_templates(self) -> List[DeviceTemplate]:
        """Get all loaded templates"""
        return list(self.templates.values())
    
    def reload(self):
        """Reload all templates from disk"""
        self.templates.clear()
        self._load_all_templates()


# ============================================================================
# Template Validator
# ============================================================================

class TemplateValidator:
    """Validates template correctness and completeness"""
    
    @staticmethod
    def validate_template(template: DeviceTemplate) -> tuple[bool, List[str]]:
        """
        Validate a template for correctness.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not template.id:
            errors.append("Template ID is required")
        
        if not template.name:
            errors.append("Template name is required")
        
        if not template.subsystems:
            errors.append("At least one subsystem is required")
        
        # Validate questions
        question_ids = set()
        for question in template.questions:
            if question.id in question_ids:
                errors.append(f"Duplicate question ID: {question.id}")
            question_ids.add(question.id)
            
            # Validate question type
            if question.type == QuestionType.CHOICE and not question.choices:
                errors.append(f"Question {question.id} is CHOICE but has no choices")
        
        # Validate rules
        for idx, rule in enumerate(template.rules):
            # Check that condition references valid question IDs
            for qid in question_ids:
                if qid in rule.condition:
                    break
            else:
                # Condition doesn't reference any known question
                if rule.condition != "True":  # Allow unconditional rules
                    errors.append(f"Rule {idx} condition may reference unknown questions")
            
            # Validate actions
            for action in rule.actions:
                if action.type == "update_constraint" and not action.subsystem:
                    errors.append(f"Rule {idx} update_constraint action missing subsystem")
        
        # Validate subsystem references in rules
        for rule in template.rules:
            for action in rule.actions:
                if action.subsystem and action.subsystem not in template.subsystems:
                    errors.append(f"Rule references unknown subsystem: {action.subsystem}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_all_templates(loader: TemplateLoader) -> Dict[str, List[str]]:
        """
        Validate all loaded templates.
        
        Returns:
            Dict mapping template_id to list of errors (empty if valid)
        """
        results = {}
        for template_id, template in loader.templates.items():
            is_valid, errors = TemplateValidator.validate_template(template)
            if not is_valid:
                results[template_id] = errors
        return results


# ============================================================================
# Template Instantiator
# ============================================================================

class TemplateInstantiator:
    """Instantiates templates with user answers"""
    
    def __init__(self, template: DeviceTemplate):
        self.template = template
        self.answers: Dict[str, Any] = {}
    
    def add_answer(self, question_id: str, answer: Any):
        """Add a user answer"""
        self.answers[question_id] = answer
    
    def evaluate_condition(self, condition: str) -> bool:
        """Evaluate a rule condition with current answers"""
        try:
            # Create safe evaluation context with answers
            context = dict(self.answers)
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return False
    
    def apply_rules(self) -> Dict[str, Any]:
        """
        Apply all rules based on current answers.
        
        Returns:
            Dict of modifications to apply to the architecture
        """
        modifications = {
            'constraint_updates': [],
            'subsystems_to_add': [],
            'subsystems_to_remove': [],
        }
        
        for rule in self.template.rules:
            if self.evaluate_condition(rule.condition):
                for action in rule.actions:
                    if action.type == "update_constraint":
                        modifications['constraint_updates'].append(action)
                    elif action.type == "add_subsystem":
                        modifications['subsystems_to_add'].append(action)
                    elif action.type == "remove_subsystem":
                        modifications['subsystems_to_remove'].append(action)
        
        return modifications
    
    def get_unanswered_questions(self, priority: Optional[QuestionPriority] = None) -> List[TemplateQuestion]:
        """Get questions that haven't been answered yet"""
        unanswered = []
        for question in self.template.questions:
            if question.id not in self.answers:
                if priority is None or question.priority == priority:
                    unanswered.append(question)
        return unanswered
    
    def is_complete(self) -> bool:
        """Check if all high-priority questions have been answered"""
        high_priority = [q for q in self.template.questions if q.priority == QuestionPriority.HIGH]
        return all(q.id in self.answers for q in high_priority)


# ============================================================================
# Helper Functions
# ============================================================================

def create_template_skeleton(template_id: str, device_type: DeviceType, name: str) -> DeviceTemplate:
    """Create a minimal template skeleton for manual editing"""
    return DeviceTemplate(
        id=template_id,
        device_type=device_type,
        name=name,
        description="Standard audio processing template with DSP capabilities",
        subsystems={
            "compute": SubsystemTemplate(
                required_functions=[],
                baseline_constraints={}
            )
        },
        questions=[],
        rules=[],
        tags=[],
        use_cases=[],
    )
