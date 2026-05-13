"""
LLM Orchestrator

All model/provider config is read from core.llm_config — change one file to
switch the entire repo between Ollama, OpenAI, or any other provider.
"""
from __future__ import annotations
import logging
import json
from typing import Dict, List, Any, Optional

from core.models import RequirementSpec, Question, QuestionTier
import core.llm_config as llm_cfg

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """LLM orchestration — provider determined by core/llm_config.py"""

    def __init__(self,
                 api_key: str | None = None,
                 base_url: str | None = None,
                 model: str | None = None):
        """
        Construct orchestrator.  All three args are optional and fall back to
        the values in core/llm_config.py so callers can use LLMOrchestrator()
        with zero arguments and it will use Ollama automatically.
        """
        import httpx
        self.model = model or llm_cfg.MODEL_RANKER
        self.client = llm_cfg.get_async_openai_client()
    
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

ENGINEERING PHILOSOPHY & EXHAUSTIVE PARSING:
1. EXHAUSTIVE SPEC MATCHING: You must explicitly infer and output constraints for EVERY relevant column in the database (e.g. max_mhz, flash_kb, sram_kb, can_count, can_fd_count, usb_fs, usb_hs, uart_count, spi_count, i2c_count, adc_count, dac_count, ethernet_count, timers_count, pwm_channels, has_fpu, has_dsp, has_crypto, has_wireless, voltage_min_v, voltage_max_v) even if only implicitly hinted at by the user.
2. INFER IMPLICIT REQUIREMENTS: If a user mentions a complex task (e.g., "Computer Vision", "Real-time ML", "Motor FOC control", "Drone Flight Controller", "Battery Powered IoT"), you MUST naturally infer the minimum viable hardware specs across ALL columns.
   - Vision/ML needs: High Flash (min 2048), High RAM (min 1024), DSP/FPU (has_dsp: 1, has_fpu: 1), High MHz (min 400).
   - Drone Flight Controller needs: Timers/PWM (min 12), UARTs (min 4 for GPS/Telem), I2C (min 2 for IMU), FPU (has_fpu: 1 for math).
   - Battery/IoT needs: Low Vmin (1.8V), maybe wireless.
3. UNIT PRECISION: You MUST output raw integers for values. Do not write "KB" or "MHz". Boolean specs (has_fpu, has_dsp) should be output as 1.

CRITICAL RULES FOR JSON KEYS:
You MUST use these EXACT keys for hard_constraints based on the database schema:
- "flash_kb": {"min": integer}
- "sram_kb": {"min": integer}
- "max_mhz": {"min": integer}
- "core": string
- "uart_count": {"min": integer}
- "spi_count": {"min": integer}
- "i2c_count": {"min": integer}
- "adc_count": {"min": integer}
- "has_fpu": {"min": integer}
- "has_dsp": {"min": integer}

Output a JSON object EXACTLY like this example:
{
  "component_type": "mcu",
  "hard_constraints": {
    "flash_kb": {"min": 2048},
    "sram_kb": {"min": 1024},
    "has_dsp": {"min": 1},
    "uart_count": {"min": 4}
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

        def _coerce_int_dict(d: dict) -> dict:
            """
            Flatten LLM outputs where values are {"min": N}, {"count": N},
            {"value": N} or {"required": N} instead of plain ints.
            RequirementSpec.interfaces is Dict[str, int].
            """
            out = {}
            for k, v in d.items():
                if isinstance(v, dict):
                    # Try all common LLM key variants in priority order
                    for key in ('min', 'count', 'value', 'required', 'max'):
                        if key in v and isinstance(v[key], (int, float)):
                            out[k] = int(v[key])
                            break
                    else:
                        # Fallback: first numeric value
                        num = next((x for x in v.values() if isinstance(x, (int, float))), None)
                        if num is not None:
                            out[k] = int(num)
                elif isinstance(v, (int, float)):
                    out[k] = int(v)
                elif isinstance(v, str) and v.isdigit():
                    out[k] = int(v)
                # skip non-numeric entries silently
            return out
        
        # Build RequirementSpec
        # Ensure assumptions is a dict (LLMs sometimes return a list)
        assumptions_raw = parsed.get('assumptions', [])
        if isinstance(assumptions_raw, list):
            assumptions = {f"assumption_{i}": val for i, val in enumerate(assumptions_raw)}
        else:
            assumptions = assumptions_raw

        raw_interfaces = parsed.get('interfaces', {})
        interfaces = _coerce_int_dict(raw_interfaces) if isinstance(raw_interfaces, dict) else {}

        spec = RequirementSpec(
            hard_constraints=hard_constraints,
            soft_preferences=_coerce_int_dict(parsed.get('soft_preferences', {})),
            environment=parsed.get('environment', {}),
            interfaces=interfaces,
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
