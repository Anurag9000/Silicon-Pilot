"""
LLM Orchestrator

OpenAI integration for parsing requirements and generating responses
with strict evidence-required enforcement.
"""
from __future__ import annotations
import logging
import json
from typing import Dict, List, Any, Optional
import openai
from openai import AsyncOpenAI

from core.models import RequirementSpec, Question, QuestionTier

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM orchestration with OpenAI"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize LLM orchestrator.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def parse_requirements(
        self,
        user_text: str,
    ) -> RequirementSpec:
        """
        Parse natural language requirements into RequirementSpec.
        
        Args:
            user_text: User's natural language requirements
        
        Returns:
            Structured RequirementSpec
        """
        logger.info("Parsing requirements with LLM")
        
        system_prompt = """You are a hardware requirements parser for an MCU selection system.

Your task is to extract structured constraints from natural language.

CRITICAL RULES:
1. Only extract constraints that are explicitly stated
2. Mark uncertain fields in "unknowns"
3. If you make assumptions, list them in "assumptions"
4. Do NOT invent specifications

Output a JSON object with:
- hard_constraints: Must-have requirements (exact values or ranges)
- soft_preferences: Nice-to-have features with weights
- environment: Temperature, certifications, etc.
- interfaces: Required peripherals (CAN, UART, SPI, I2C, USB, etc.)
- unknowns: List of missing critical information
- assumptions: List of assumptions made

Example input: "Need Cortex-M4, at least 512KB flash, 2 CAN, QFP package"
Example output:
{
  "hard_constraints": {
    "core": "ARM Cortex-M4",
    "flash_kb": {"min": 512},
    "can_count": {"min": 2},
    "package_family": ["QFP"]
  },
  "interfaces": {
    "can": 2
  },
  "unknowns": ["temp_range", "ram_kb", "clock_mhz"],
  "assumptions": []
}
"""
        
        user_prompt = f"Parse this requirement:\n\n{user_text}"
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,  # Deterministic
        )
        
        # Parse response
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Build RequirementSpec
        spec = RequirementSpec(
            hard_constraints=parsed.get('hard_constraints', {}),
            soft_preferences=parsed.get('soft_preferences', {}),
            environment=parsed.get('environment', {}),
            interfaces=parsed.get('interfaces', {}),
            unknowns=parsed.get('unknowns', []),
            assumptions=parsed.get('assumptions', []),
        )
        
        logger.info(f"Parsed spec with {len(spec.unknowns)} unknowns")
        
        return spec
    
    async def generate_questions(
        self,
        spec: RequirementSpec,
        candidates_count: int,
    ) -> List[Question]:
        """
        Generate clarifying questions based on unknowns.
        
        Args:
            spec: Current requirement specification
            candidates_count: Number of candidates matching current spec
        
        Returns:
            List of questions to ask
        """
        logger.info("Generating questions with LLM")
        
        system_prompt = """You are a hardware requirements clarification assistant.

Your task is to generate clarifying questions to help narrow down MCU selection.

CRITICAL RULES:
1. Ask about unknowns that most affect the selection
2. Prioritize questions by information gain
3. Batch related questions together
4. Explain WHY you're asking each question
5. Provide reasonable options when applicable

Question tiers:
- TIER_1: Critical for basic filtering (temp range, core, memory)
- TIER_2: Important for ranking (power, cost, ecosystem)
- TIER_3: Nice-to-have (future-proofing, second-source)

Output JSON array of questions with:
- field_name: The field being asked about
- question_text: The actual question
- why_asking: Explanation of why this matters
- tier: Question tier (tier_1, tier_2, tier_3)
- options: Optional list of common answers
"""
        
        user_prompt = f"""Current spec:
Unknowns: {spec.unknowns}
Assumptions: {spec.assumptions}
Candidates matching current spec: {candidates_count}

Generate 3-5 high-value questions to narrow down the selection."""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Slight creativity for question phrasing
        )
        
        # Parse response
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Build Question objects
        questions = []
        for q_data in parsed.get('questions', []):
            question = Question(
                field_name=q_data['field_name'],
                question_text=q_data['question_text'],
                why_asking=q_data.get('why_asking', ''),
                tier=QuestionTier(q_data.get('tier', 'tier_2')),
                options=q_data.get('options'),
            )
            questions.append(question)
        
        logger.info(f"Generated {len(questions)} questions")
        
        return questions
    
    async def generate_explanation(
        self,
        spec: RequirementSpec,
        candidates: List[Dict[str, Any]],
        top_candidate: Dict[str, Any],
    ) -> str:
        """
        Generate human-readable explanation of recommendation.
        
        Args:
            spec: Requirement specification
            candidates: All candidates
            top_candidate: Top recommended part
        
        Returns:
            Explanation text
        """
        logger.info("Generating explanation with LLM")
        
        system_prompt = """You are a hardware recommendation explainer.

Your task is to explain WHY a particular MCU was recommended.

CRITICAL RULES:
1. Reference specific constraints from the requirement
2. Explain how the top choice satisfies each constraint
3. Mention key differentiators vs other candidates
4. Be concise but informative
5. Use technical language appropriate for engineers

Format:
- Start with a one-sentence summary
- List key matches (constraints satisfied)
- Explain ranking factors (headroom, ecosystem, etc.)
- Note any trade-offs or considerations
"""
        
        user_prompt = f"""Requirement:
{json.dumps(spec.model_dump(), indent=2)}

Top recommendation: {top_candidate['mpn']} ({top_candidate['manufacturer']})
Total candidates: {len(candidates)}

Explain why this is the best choice."""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.5,
        )
        
        explanation = response.choices[0].message.content
        
        return explanation
    
    async def format_near_miss_suggestion(
        self,
        failed_constraint: str,
        current_value: Any,
        required_value: Any,
    ) -> str:
        """
        Generate human-friendly near-miss suggestion.
        
        Args:
            failed_constraint: Constraint that failed
            current_value: Actual value
            required_value: Required value
        
        Returns:
            Suggestion text
        """
        prompt = f"""A candidate MCU failed this constraint:
- Constraint: {failed_constraint}
- Required: {required_value}
- Actual: {current_value}

Generate a concise suggestion for how to relax this constraint.
Example: "Consider relaxing flash requirement to ≥256KB to include STM32F405"
"""
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=100,
        )
        
        return response.choices[0].message.content.strip()
