"""
Question Engine

Information gain-based question selection with batching and stop criteria.
"""

import logging
from typing import Dict, List, Any, Tuple, Optional, Set
from collections import defaultdict

from core.models import RequirementSpec, Question, QuestionTier, Answer

logger = logging.getLogger(__name__)


class QuestionEngine:
    """Question selection with information gain"""
    
    def __init__(self):
        """Initialize question engine"""
        self.max_questions_per_turn = 5
        self.stop_threshold = 0.1  # 10% change in top-N
    
    def select_questions(
        self,
        spec: RequirementSpec,
        candidates: List[Dict[str, Any]],
        max_questions: Optional[int] = None,
    ) -> List[Question]:
        """
        Select highest-value questions to ask.
        
        Args:
            spec: Current requirement specification
            candidates: Current candidate set
            max_questions: Maximum questions to return
        
        Returns:
            List of questions, prioritized by information gain
        """
        max_q = max_questions or self.max_questions_per_turn
        
        logger.info(f"Selecting questions from {len(spec.unknowns)} unknowns")
        
        if not spec.unknowns:
            return []
        
        # Calculate information gain for each unknown field
        field_gains = self._calculate_information_gains(
            spec.unknowns,
            candidates,
        )
        
        # Sort by information gain
        sorted_fields = sorted(
            field_gains.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Build questions for top fields
        questions = []
        for field_name, gain in sorted_fields[:max_q]:
            question = self._build_question(field_name, candidates, gain)
            if question:
                questions.append(question)
        
        logger.info(f"Selected {len(questions)} questions")
        
        return questions
    
    def _calculate_information_gains(
        self,
        unknown_fields: List[str],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Calculate information gain for each unknown field.
        
        Information gain = how much this field reduces candidate set variance
        
        Returns:
            Dict of field_name -> gain score
        """
        gains = {}
        
        for field in unknown_fields:
            value_counts = defaultdict(int)

            for candidate in candidates:
                value = candidate.get(field)
                if value is not None:
                    value_counts[value] += 1

            if not value_counts:
                gains[field] = 0.0
                continue

            # Shannon entropy: H = -Σ p * log2(p)
            # Higher entropy → this field has more variance → asking about it narrows
            # the candidate set the most.
            import math
            total = len(candidates)
            entropy = 0.0

            for count in value_counts.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)

            # Weight by number of unique values so fields with many distinct
            # values (e.g. exact MHz) rank above binary flags.
            unique_values  = len(value_counts)
            normalized_gain = entropy * unique_values

            gains[field] = normalized_gain
        
        return gains
    
    def _build_question(
        self,
        field_name: str,
        candidates: List[Dict[str, Any]],
        information_gain: float,
    ) -> Optional[Question]:
        """
        Build a question for a field.
        
        Args:
            field_name: Field to ask about
            candidates: Current candidates
            information_gain: Calculated information gain
        
        Returns:
            Question object
        """
        # Field-specific question templates
        question_templates = {
            'temp_min_c': {
                'text': 'What is the minimum operating temperature required?',
                'why': 'Temperature range affects part availability and cost.',
                'tier': QuestionTier.TIER_1,
                'options': ['-40°C', '-20°C', '0°C'],
            },
            'temp_max_c': {
                'text': 'What is the maximum operating temperature required?',
                'why': 'Temperature range affects part availability and cost.',
                'tier': QuestionTier.TIER_1,
                'options': ['70°C', '85°C', '105°C', '125°C'],
            },
            'ram_kb': {
                'text': 'How much RAM (SRAM) do you need?',
                'why': 'RAM size affects available parts and cost.',
                'tier': QuestionTier.TIER_1,
                'options': ['32KB', '64KB', '128KB', '256KB', '512KB'],
            },
            'sram_kb': {
                'text': 'How much SRAM do you need?',
                'why': 'SRAM size affects available parts and cost.',
                'tier': QuestionTier.TIER_1,
                'options': ['32KB', '64KB', '128KB', '256KB', '512KB'],
            },
            'clock_mhz': {
                'text': 'What clock speed do you need?',
                'why': 'Clock speed affects performance and power consumption.',
                'tier': QuestionTier.TIER_2,
                'options': ['48MHz', '72MHz', '120MHz', '168MHz', '400MHz'],
            },
            'max_mhz': {
                'text': 'What maximum clock speed do you need?',
                'why': 'Clock speed affects performance and power consumption.',
                'tier': QuestionTier.TIER_2,
                'options': ['48MHz', '72MHz', '120MHz', '168MHz', '400MHz'],
            },
            'cost_usd': {
                'text': 'What is your target cost per unit?',
                'why': 'Cost affects part selection and project budget.',
                'tier': QuestionTier.TIER_2,
                'options': ['<$1', '<$3', '<$5', '<$10', 'No limit'],
            },
            'has_fpu': {
                'text': 'Do you need a floating-point unit (FPU)?',
                'why': 'FPU accelerates floating-point math operations.',
                'tier': QuestionTier.TIER_2,
                'options': ['Yes', 'No', 'Nice to have'],
            },
            'has_wireless': {
                'text': 'Do you need built-in wireless (WiFi/BLE)?',
                'why': 'Wireless integration affects part selection and cost.',
                'tier': QuestionTier.TIER_2,
                'options': ['Yes', 'No', 'Nice to have'],
            },
            'package_family': {
                'text': 'What package type do you prefer?',
                'why': 'Package affects PCB design and assembly.',
                'tier': QuestionTier.TIER_1,
                'options': ['QFP', 'QFN', 'BGA', 'Any'],
            },
        }
        
        template = question_templates.get(field_name)
        
        if template:
            return Question(
                field_name=field_name,
                question_text=template['text'],
                why_asking=template['why'],
                tier=template['tier'],
                options=template['options'],
            )
        
        # Generic question for unknown fields
        return Question(
            field_name=field_name,
            question_text=f"What value do you need for {field_name}?",
            why_asking=f"This field affects the selection (information gain: {information_gain:.2f})",
            tier=QuestionTier.TIER_2,
        )
    
    def apply_answers(
        self,
        spec: RequirementSpec,
        answers: List[Answer],
    ) -> RequirementSpec:
        """
        Apply user answers to update RequirementSpec.
        
        Args:
            spec: Current specification
            answers: User answers
        
        Returns:
            Updated specification
        """
        logger.info(f"Applying {len(answers)} answers")
        
        # Pydantic v2 uses model_copy(); v1 uses copy() — support both
        try:
            updated_spec = spec.model_copy(deep=True)
        except AttributeError:
            updated_spec = spec.copy(deep=True)
        
        for answer in answers:
            field_name = answer.field_name
            value = answer.value
            
            # Remove from unknowns
            if field_name in updated_spec.unknowns:
                updated_spec.unknowns.remove(field_name)
            
            # Add to hard constraints or soft preferences
            if answer.is_hard_constraint:
                updated_spec.hard_constraints[field_name] = value
            else:
                updated_spec.soft_preferences[field_name] = {
                    'value': value,
                    'weight': 0.5,
                }
        
        return updated_spec
    
    def check_stop_criteria(
        self,
        previous_top_n: List[str],
        current_top_n: List[str],
        n: int = 10,
    ) -> bool:
        """
        Check if we should stop asking questions.
        
        Args:
            previous_top_n: Previous top-N MPNs
            current_top_n: Current top-N MPNs
            n: Size of top-N
        
        Returns:
            True if should stop asking questions
        """
        if not previous_top_n or not current_top_n:
            return False
        
        # Calculate overlap
        prev_set = set(previous_top_n[:n])
        curr_set = set(current_top_n[:n])
        
        overlap = len(prev_set & curr_set)
        overlap_ratio = overlap / n
        
        # Stop if top-N is stable (>90% overlap)
        should_stop = overlap_ratio > (1.0 - self.stop_threshold)
        
        if should_stop:
            logger.info(f"Stop criteria met: {overlap_ratio:.1%} overlap in top-{n}")
        
        return should_stop
    
    def batch_questions_by_tier(
        self,
        questions: List[Question],
    ) -> Dict[QuestionTier, List[Question]]:
        """
        Batch questions by tier.
        
        Args:
            questions: List of questions
        
        Returns:
            Dict of tier -> questions
        """
        batches = defaultdict(list)
        
        for question in questions:
            batches[question.tier].append(question)
        
        return dict(batches)
