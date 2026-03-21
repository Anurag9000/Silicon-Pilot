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
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize LLM orchestrator.
        """
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )
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
        
        system_prompt = """You are a world-class Senior Systems Architect and Hardware Engineer.
Your task is to extract structured engineering constraints from user natural language.

ENGINEERING PHILOSOPHY:
1. INFER REQUIREMENTS: If a user mentions a complex task (e.g., "Computer Vision", "Real-time ML", "Motor FOC control"), you must naturally infer the minimum viable hardware specs. 
   - Vision/ML needs: High Flash (min 2048), High RAM (min 1024), and DSP/FPU capable cores (Cortex-M7).
2. UNIT PRECISION: You MUST output raw integers for values. Do not write "KB" or "MHz".

CRITICAL RULES FOR JSON KEYS:
You MUST use these EXACT keys for hard_constraints:
- "flash_kb": {"min": integer}
- "sram_kb": {"min": integer}
- "core": string
- "can_count": {"min": integer}

Output a JSON object EXACTLY like this example:
{
  "component_type": "mcu",
  "hard_constraints": {
    "flash_kb": {"min": 2048},
    "sram_kb": {"min": 1024},
    "core": "ARM Cortex-M7",
    "can_count": {"min": 2}
  },
  "soft_preferences": {},
  "environment": {},
  "interfaces": {},
  "unknowns": [],
  "assumptions": ["Vision requires M7 and high memory"]
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
            temperature=0.0,
        )
        
        # Parse response
        content = response.choices[0].message.content
        parsed = json.loads(content)
        
        # Inject component_type into hard_constraints for HardFilter to use
        hard_constraints = parsed.get('hard_constraints', {})
        if 'component_type' in parsed:
            hard_constraints['component_type'] = parsed['component_type']
        
        # Build RequirementSpec
        # Ensure assumptions is a dict (LLMs sometimes return a list)
        assumptions_raw = parsed.get('assumptions', [])
        if isinstance(assumptions_raw, list):
            assumptions = {f"assumption_{i}": val for i, val in enumerate(assumptions_raw)}
        else:
            assumptions = assumptions_raw

        spec = RequirementSpec(
            hard_constraints=hard_constraints,
            soft_preferences=parsed.get('soft_preferences', {}),
            environment=parsed.get('environment', {}),
            interfaces=parsed.get('interfaces', {}),
            unknowns=parsed.get('unknowns', []),
            assumptions=assumptions,
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
        """
        logger.info("Generating questions with LLM")
        
        system_prompt = """
You are a hardware requirements clarification assistant.
Your task is to generate clarifying questions to help narrow down MCU selection.

CRITICAL RULES:
1. Ask about unknowns that most affect the selection
2. Prioritize questions by information gain
3. Batch related questions together
4. Explain why you're asking each question
5. Provide reasonable options when applicable

Output JSON array of questions with:
- field_name: The field being asked about
- question_text: The actual question
- why_asking: Explanation of why this matters
- tier: Question tier (tier_1, tier_2, tier_3)
- options: Optional list of common answers
"""
        
        user_prompt = f"Constraints so far: {spec.model_dump_json()}\nCandidates matching: {candidates_count}"
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        
        data = json.loads(response.choices[0].message.content)
        questions = []
        for q in data.get('questions', []):
            questions.append(Question(**q))
            
        return questions

    async def generate_explanation(
        self,
        spec: RequirementSpec,
        candidates: List[Dict[str, Any]],
        top_candidate: Dict[str, Any],
    ) -> str:
        """
        Generate a human-readable explanation for why the top candidate was chosen.
        """
        logger.info("Generating explanation with LLM")
        
        system_prompt = """
You are a hardware engineer explaining component selection.
Explain why the top choice is the best fit for the user's requirements.
Compare it briefly to the other candidates if relevant.
Highlight how it satisfies critical constraints.
"""
        
        user_prompt = f"""
Requirement:
{spec.model_dump_json()}

Top Choice:
{json.dumps(top_candidate, default=str)}

Other Candidates:
{json.dumps(candidates[:3], default=str)}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=200,
        )
        
        return response.choices[0].message.content.strip()
