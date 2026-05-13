"""
Rigorous Explainer Module

All model/provider config is read from core.llm_config — change one file to
switch the entire repo between Ollama, OpenAI, or any other provider.
"""
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import UUID
from core.models import RequirementSpec
import core.llm_config as llm_cfg

logger = logging.getLogger(__name__)


def _json_safe(obj):
    """JSON serializer that handles UUID, datetime, Decimal, and bytes objects."""
    if isinstance(obj, UUID):
        return str(obj)
    from datetime import datetime, date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

class RigorousExplainer:
    def __init__(self,
                 api_key: str | None = None,
                 base_url: str | None = None,
                 model: str | None = None):
        """All args optional — falls back to core/llm_config.py."""
        self.model = model or llm_cfg.MODEL_DEBATE
        self.client = llm_cfg.get_async_openai_client()

    async def generate_comparison_matrix(
        self, 
        spec: RequirementSpec, 
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generates a rigorous comparison matrix between the top candidates.
        """
        logger.info(f"Generating comparison matrix for {len(candidates)} candidates")
        
        system_prompt = """You are a senior hardware systems architect. 
Generate a technical comparison matrix for the following electronic components.
Compare them across:
1. Core hardware specs (Clock, Flash, RAM)
2. Peripheral sets (matched against user requirements)
3. Power efficiency
4. Ecosystem and Longevity
5. Specific technical trade-offs

Format the output as a JSON object with:
- headers: List of strings (feature names)
- rows: List of objects, each containing:
    - mpn: Part number
    - manufacturer: Manufacturer
    - values: Dict mapping headers to specific data/comments
- conclusion: A rigorous summary of which part wins in which scenario.
"""
        
        user_prompt = f"""Requirement Spec:
{spec.model_dump_json(indent=2)}

Candidates:
{json.dumps(candidates[:3], indent=2, default=_json_safe)}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)

    async def conduct_architect_debate(
        self,
        spec: RequirementSpec,
        top_candidate: Dict[str, Any],
        alternative_candidate: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Simulates a debate between two senior architects to ensure objective choice.
        Inspired by RigorousRAG's Scientific Debate tool.
        """
        logger.info(f"Conducting architect debate between {top_candidate['mpn']} and {alternative_candidate['mpn']}")
        
        debate_turns = []
        
        # Turn 1: Architect A (Pro-Top Candidate)
        prompt_a = f"""You are Architect A. Argue WHY {top_candidate['mpn']} is the strictly better choice for these requirements:
{spec.model_dump_json()}
vs the alternative {alternative_candidate['mpn']}. Focus on technical superiority and risk mitigation."""
        
        res_a = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt_a}]
        )
        debate_turns.append({"architect": "Architect A", "argument": res_a.choices[0].message.content})
        
        # Turn 2: Architect B (The Skeptic / Pro-Alternative)
        prompt_b = f"""You are Architect B. Challenge Architect A's argument. Point out the weaknesses of {top_candidate['mpn']} 
and argue for {alternative_candidate['mpn']}. Mention hidden costs, power consumption, or ecosystem lock-in."""
        
        res_b = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt_a},
                {"role": "assistant", "content": res_a.choices[0].message.content},
                {"role": "user", "content": prompt_b}
            ]
        )
        debate_turns.append({"architect": "Architect B", "argument": res_b.choices[0].message.content})
        
        return debate_turns

    async def generate_architect_review(
        self,
        spec: 'RequirementSpec',
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Dream Spec #4: AI Peer Review — Acts as a senior hardware engineer reviewing
        the full design and returning a structured verdict with actionable notes.
        Returns: { verdict: 'green'|'amber'|'red', summary: str, notes: [str] }
        """
        logger.info(f"Generating Architect's Peer Review for top {len(candidates)} candidates")

        top = candidates[0] if candidates else {}
        all_mpns = [c.get('mpn', '?') for c in candidates[:3]]

        system_prompt = """You are a senior hardware engineer with 20+ years of experience reviewing embedded system designs.
Your job: Review the proposed component selection and requirements and give an honest, critical assessment.

OUTPUT FORMAT — respond with ONLY valid JSON:
{
  "verdict": "green" | "amber" | "red",
  "verdict_reason": "One-sentence summary of verdict.",
  "architect_notes": ["Note 1", "Note 2", "Note 3"],
  "overkill_warnings": ["Any over-engineering or overkill warning, if any"],
  "missing_considerations": ["Missing aspects the user hasn't thought of"],
  "recommended_action": "Final one-sentence engineer recommendation"
}

Verdict guide:
- green: Good selection, proceed with confidence
- amber: Acceptable but has notable trade-offs, review notes before committing
- red: Major design concern, revisit before committing silicon
"""

        user_prompt = f"""Requirements:
{spec.model_dump_json(indent=2)}

Top recommended part: {top.get('mpn', 'N/A')} ({top.get('manufacturer', '')})
  - Core: {top.get('core', '?')}
  - Flash: {top.get('flash_kb', '?')} KB, RAM: {top.get('sram_kb', '?')} KB
  - Max MHz: {top.get('max_mhz', '?')}
  - Cost: ${top.get('cost_usd', '?')}

Other candidates considered: {', '.join(all_mpns[1:])}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Peer review failed: {e}")
            return {
                "verdict": "amber",
                "verdict_reason": "Could not complete automated review.",
                "architect_notes": [str(e)],
                "overkill_warnings": [],
                "missing_considerations": [],
                "recommended_action": "Please review the design manually."
            }

    async def generate_exhaustive_parameter_review(
        self,
        spec: 'RequirementSpec',
        candidate: Dict[str, Any],
        datasheet_params: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Exhaustively verifies EVERY SINGLE PARAMETER — from the DB spec fields
        AND from real datasheet PDF extractions (datasheet_params).

        Returns a row-by-row breakdown with section, source page, and justification.
        """
        logger.info(f"Generating exhaustive parameter review for {candidate.get('mpn', 'Unknown')}")

        combined_specs = dict(candidate)
        if 'specs' in combined_specs:
            combined_specs.update(combined_specs.pop('specs'))

        # Build PDF parameter section for the prompt
        pdf_param_lines = ""
        if datasheet_params:
            by_section: Dict[str, List[Dict]] = {}
            for p in datasheet_params:
                s = p.get("section", "other")
                by_section.setdefault(s, []).append(p)

            lines = []
            for section, rows in sorted(by_section.items()):
                lines.append(f"\n### {section.replace('_', ' ').title()}")
                for r in rows:
                    lines.append(
                        f"  • {r.get('parameter', '')}: "
                        f"min={r.get('min_value', '-')} "
                        f"typ={r.get('typ_value', '-')} "
                        f"max={r.get('max_value', '-')} "
                        f"{r.get('unit', '')}  "
                        f"[cond: {r.get('conditions') or 'n/a'}]  "
                        f"[page {r.get('source_page', '?')}]"
                    )
            pdf_param_lines = "\n".join(lines)

        system_prompt = """You are a meticulous hardware systems architect specializing in Explainable AI (XAI) transparency for embedded MCU selection.

TASK: Perform an EXHAUSTIVE, parameter-by-parameter verification of the component against user requirements.

RULES:
1. Evaluate EVERY SINGLE parameter listed — from DB fields AND from PDF extraction sections.
2. Each parameter = its own separate JSON object. Never summarize or group.
3. For PDF-sourced params, include section name and PDF page number in the justification.
4. fit_level must be exactly ONE of: "Exceeds" | "Meets" | "Warning" | "Fails"
5. Write precise, technical justifications with actual numbers and engineering rationale.

OUTPUT — respond ONLY with valid JSON (no markdown):
{
  "exhaustive_review": [
    {
      "section": "dc_characteristics",
      "parameter": "VIH — Input High Voltage",
      "datasheet_value": "0.7×VDD to VDD+0.4 V",
      "required_value": "CMOS 3.3V compatible",
      "fit_level": "Meets",
      "source_page": 87,
      "architect_justification": "Threshold 0.7×3.3V=2.31V; nominal output 2.4V gives 90mV margin. Adequate."
    }
  ]
}

Cover ALL: Flash, RAM, MHz, CAN interfaces, ADC, SPI, I2C, USB, Timers, FPU, voltage range, power modes, thermal resistance, package temp range, GPIO drive strength, clock accuracy, absolute max ratings, AC timing, and any other parameter extracted from the PDF.
"""
        pdf_block = (
            f"\n=== PDF EXTRACTION ({len(datasheet_params)} params from actual datasheet pages) ===\n{pdf_param_lines}"
            if datasheet_params
            else "\n[No PDF extraction available for this part — evaluate DB fields only.]\n"
        )

        user_prompt = f"""## User Requirements
{spec.model_dump_json(indent=2)}

## Component Record: {candidate.get('mpn')}
{json.dumps(combined_specs, indent=2, default=_json_safe)}
{pdf_block}

Perform exhaustive, traceable, line-by-line verification of every parameter above."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Exhaustive review failed: {e}")
            return {"exhaustive_review": []}

