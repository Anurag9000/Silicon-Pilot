"""
Rigorous Explainer Module

Implements advanced explainability features inspired by RigorousRAG:
1. Comparison Matrix
2. Multi-Agent Debate (Choice Justification)
3. Evidence Grounding
"""
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from core.models import RequirementSpec

logger = logging.getLogger(__name__)

class RigorousExplainer:
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: str = "gpt-4o"):
        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=base_url,
            timeout=httpx.Timeout(300.0, connect=10.0)
        )
        self.model = model

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
{json.dumps(candidates[:3], indent=2)}
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
        candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Takes a single candidate and exhaustively verifies EVERY SINGLE PARAMETER available in the database
        against the user's base requirements constraint. Returns a row-by-row breakdown.
        """
        logger.info(f"Generating exhaustive parameter review for {candidate.get('mpn', 'Unknown')}")

        system_prompt = """You are a meticulous, highly-critical hardware systems architect.
Your job is to provide Explainable AI (XAI) transparency by reviewing EVERY SINGLE KNOWN DATASHEET PARAMETER of the provided component against the user's workload requirements.

You must evaluate each parameter strictly and provide a JSON array. DO NOT summarize or skip metrics.
If the component data contains Flash, RAM, MHz, CAN counts, ADC bits, Thermal Resistance, Voltage, Timer counts etc., yield a separate JSON object for each one.

OUTPUT FORMAT — respond with ONLY valid JSON:
{
  "exhaustive_review": [
    {
      "parameter": "Wait States / Flash Memory Limit",
      "datasheet_value": "1024 KB",
      "required_value": "512 KB min",
      "fit_level": "Exceeds",  // Must be one of: "Exceeds", "Meets", "Warning", "Fails"
      "architect_justification": "Provides ample headroom for OTA payload boundaries. Overprovisioned safely."
    },
    ...
  ]
}

Be exhaustive. Include all electrical, thermal, structural, and silicon capabilities present in the JSON.
"""

        # Serialize the combined candidate dict so the prompt sees all top-level and spec fields
        combined_specs = dict(candidate)
        if 'specs' in combined_specs:
            combined_specs.update(combined_specs.pop('specs'))

        user_prompt = f"""Target Workload Requirements:
{spec.model_dump_json(indent=2)}

Datasheet Dump for {candidate.get('mpn')}:
{json.dumps(combined_specs, indent=2)}

Perform the exhaustive line-by-line verification."""

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
