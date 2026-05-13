"""
LLM-Enhanced Template Matching — provider/model from core/llm_config.py
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import json
import os
import core.llm_config as llm_cfg

from templates.template_system import TemplateLoader, DeviceTemplate


# ============================================================================
# Models
# ============================================================================

class SemanticMatch(BaseModel):
    """Semantic template match with LLM reasoning"""
    template_id: str
    template_name: str
    confidence: float  # 0.0-1.0
    reasoning: str
    key_alignments: List[str]  # What matched well
    potential_gaps: List[str]  # What might be missing


# ============================================================================
# LLM-Enhanced Template Matcher
# ============================================================================

class LLMTemplateMatcher:
    """
    Uses LLM to semantically match user intent to templates.
    
    Better than keyword matching because it understands:
    - Synonyms and related concepts
    - Implicit requirements
    - Use case similarity
    - Domain knowledge
    """
    
    def __init__(
        self,
        template_loader: TemplateLoader,
        api_key: Optional[str] = None,
        model: str | None = None,
    ):
        self.loader = template_loader
        self.model = model or llm_cfg.MODEL_PARSER
        self.client = llm_cfg.get_openai_client()
    
    def match_templates(
        self,
        user_input: str,
        top_k: int = 5
    ) -> List[SemanticMatch]:
        """
        Match templates using semantic understanding.
        
        Args:
            user_input: User's natural language description
            top_k: Number of matches to return
            
        Returns:
            List of SemanticMatch sorted by confidence
        """
        
        if not self.client:
            # Fallback to keyword matching
            return self._fallback_match(user_input, top_k)
        
        # Get all templates
        templates = self.loader.list_all_templates()
        
        # Build prompt
        prompt = self._build_matching_prompt(user_input, templates)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent matching
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse matches
            matches = []
            for match_data in result.get("matches", [])[:top_k]:
                matches.append(SemanticMatch(
                    template_id=match_data["template_id"],
                    template_name=match_data["template_name"],
                    confidence=match_data["confidence"],
                    reasoning=match_data["reasoning"],
                    key_alignments=match_data.get("key_alignments", []),
                    potential_gaps=match_data.get("potential_gaps", [])
                ))
            
            return matches
            
        except Exception as e:
            print(f"LLM template matching failed: {e}")
            return self._fallback_match(user_input, top_k)
    
    def _get_system_prompt(self) -> str:
        """System prompt for template matching"""
        return """You are an expert hardware engineer assistant. Your task is to match user requirements to the most appropriate hardware design templates.

Analyze the user's description and match it to templates based on:
1. **Primary Function**: What is the main purpose?
2. **Communication/Interfaces**: What protocols or connections are needed?
3. **Environment**: Where will it be used?
4. **Constraints**: Power, size, cost, etc.
5. **Use Case Similarity**: Similar applications or domains

Consider:
- Synonyms (e.g., "motor driver" = "motor controller")
- Implicit requirements (e.g., "automotive" implies temperature range, EMC)
- Related concepts (e.g., "BLDC" implies PWM, current sensing)
- Domain knowledge (e.g., "drone" needs IMU, ESC, radio)

Respond with JSON:
{
    "matches": [
        {
            "template_id": "can_motor_controller_v1",
            "template_name": "CAN Motor Controller",
            "confidence": 0.95,
            "reasoning": "Primary function is motor control, CAN is the communication protocol, BLDC motor type specified",
            "key_alignments": [
                "Motor control is primary function",
                "CAN communication explicitly mentioned",
                "BLDC motor type matches template capabilities"
            ],
            "potential_gaps": [
                "No mention of current rating - will need to ask",
                "Supply voltage not specified"
            ]
        }
    ]
}

Confidence guidelines:
- 0.9-1.0: Perfect match, all key requirements align
- 0.7-0.9: Strong match, most requirements align
- 0.5-0.7: Good match, core function aligns but some gaps
- 0.3-0.5: Partial match, related but not ideal
- 0.0-0.3: Weak match, only tangentially related"""
    
    def _build_matching_prompt(
        self,
        user_input: str,
        templates: List[DeviceTemplate]
    ) -> str:
        """Build prompt for template matching"""
        
        prompt = f"""User Request:
"{user_input}"

Available Templates:
"""
        
        for template in templates:
            prompt += f"""
{template.id}:
  Name: {template.name}
  Type: {template.device_type.value if template.device_type else 'unknown'}
  Description: {template.description}
  Tags: {', '.join(template.tags)}
  Key Features: {', '.join(template.subsystems.keys())}
"""
        
        prompt += """
Match the user's request to the most appropriate templates. Return top 5 matches with confidence scores and reasoning.
"""
        
        return prompt
    
    def _fallback_match(
        self,
        user_input: str,
        top_k: int
    ) -> List[SemanticMatch]:
        """Fallback keyword-based matching"""
        
        user_lower = user_input.lower()
        templates = self.loader.list_all_templates()
        
        matches = []
        for template in templates:
            score = 0.0
            alignments = []
            
            # Check device type
            if template.device_type and template.device_type.value in user_lower:
                score += 0.3
                alignments.append(f"Device type: {template.device_type.value}")
            
            # Check tags
            for tag in template.tags:
                if tag.lower() in user_lower:
                    score += 0.1
                    alignments.append(f"Tag: {tag}")
            
            # Check name
            name_words = template.name.lower().split()
            for word in name_words:
                if word in user_lower and len(word) > 3:
                    score += 0.05
            
            if score > 0:
                matches.append(SemanticMatch(
                    template_id=template.id,
                    template_name=template.name,
                    confidence=min(score, 1.0),
                    reasoning=f"Keyword-based match (LLM unavailable)",
                    key_alignments=alignments,
                    potential_gaps=[]
                ))
        
        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches[:top_k]


# ============================================================================
# Natural Language Explanation Generator
# ============================================================================

class ExplanationGenerator:
    """
    Generates natural language explanations for design decisions.
    
    Makes technical decisions understandable to users.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if OpenAI and self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
    
    def explain_component_selection(
        self,
        component: Dict[str, Any],
        requirements: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        user_level: str = "intermediate"
    ) -> str:
        """
        Explain why a component was selected.
        
        Args:
            component: Selected component
            requirements: User requirements
            alternatives: Alternative components considered
            user_level: beginner/intermediate/expert
            
        Returns:
            Natural language explanation
        """
        
        if not self.client:
            return self._fallback_explanation(component, requirements)
        
        prompt = self._build_explanation_prompt(
            component, requirements, alternatives, user_level
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_explanation_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"LLM explanation failed: {e}")
            return self._fallback_explanation(component, requirements)
    
    def _get_explanation_system_prompt(self) -> str:
        """System prompt for explanations"""
        return """You are a helpful hardware engineer explaining design decisions to users.

Your explanations should:
1. Be clear and understandable
2. Explain WHY, not just WHAT
3. Mention key benefits
4. Note any trade-offs
5. Suggest alternatives when relevant
6. Use analogies when helpful
7. Avoid unnecessary jargon

Adapt your language to the user's level:
- Beginner: Simple terms, more analogies, explain basics
- Intermediate: Technical but clear, assume basic knowledge
- Expert: Concise, technical details, focus on trade-offs

Format:
- Use numbered lists for multiple points
- Bold key terms
- Keep paragraphs short
- End with alternatives if relevant"""
    
    def _build_explanation_prompt(
        self,
        component: Dict[str, Any],
        requirements: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        user_level: str
    ) -> str:
        """Build explanation prompt"""
        
        prompt = f"""Explain why we selected this component.

User Level: {user_level}

Selected Component:
- Part Number: {component.get('mpn', 'Unknown')}
- Description: {component.get('description', 'Unknown')}
- Price: ${component.get('price_usd', 0):.2f}
- Key Specs: {json.dumps(component.get('specs', {}), indent=2)}

User Requirements:
{json.dumps(requirements, indent=2)}

Alternatives Considered:
"""
        
        for alt in alternatives[:3]:
            prompt += f"""
- {alt.get('mpn', 'Unknown')}: ${alt.get('price_usd', 0):.2f}
  {alt.get('description', 'Unknown')}
"""
        
        prompt += """
Explain why the selected component is the best choice. Focus on how it meets requirements and why it's better than alternatives.
"""
        
        return prompt
    
    def _fallback_explanation(
        self,
        component: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> str:
        """Fallback explanation when LLM unavailable"""
        
        mpn = component.get('mpn', 'Unknown')
        price = component.get('price_usd', 0)
        description = component.get('description', 'Unknown')
        
        return f"""Selected {mpn} (${price:.2f})

{description}

This component meets your requirements and offers good value for the specifications needed."""


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """Demonstrate LLM-enhanced matching and explanations"""
    
    # Example 1: Template Matching
    print("=== LLM Template Matching ===\n")
    
    user_input = "I want to build a motor controller for a BLDC motor with CAN communication"
    
    template_loader = TemplateLoader("../templates")
    matcher = LLMTemplateMatcher(template_loader)
    
    matches = matcher.match_templates(user_input, top_k=3)
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.template_name} (confidence: {match.confidence:.0%})")
        print(f"   Reasoning: {match.reasoning}")
        print(f"   Alignments: {', '.join(match.key_alignments)}")
        if match.potential_gaps:
            print(f"   Gaps: {', '.join(match.potential_gaps)}")
        print()
    
    # Example 2: Component Explanation
    print("\n=== Component Selection Explanation ===\n")
    
    component = {
        "mpn": "STM32F405RGT6",
        "description": "ARM Cortex-M4, 168MHz, 1MB Flash, 192KB RAM",
        "price_usd": 5.50,
        "specs": {
            "flash_kb": 1024,
            "ram_kb": 192,
            "mhz": 168,
            "can_count": 2
        }
    }
    
    requirements = {
        "min_flash_kb": 256,
        "min_ram_kb": 64,
        "can_required": True,
        "motor_type": "BLDC"
    }
    
    alternatives = [
        {
            "mpn": "STM32F103RBT6",
            "description": "ARM Cortex-M3, 72MHz, 128KB Flash",
            "price_usd": 3.50
        },
        {
            "mpn": "STM32H743VIT6",
            "description": "ARM Cortex-M7, 480MHz, 2MB Flash",
            "price_usd": 9.20
        }
    ]
    
    explainer = ExplanationGenerator()
    explanation = explainer.explain_component_selection(
        component, requirements, alternatives, user_level="intermediate"
    )
    
    print(explanation)


if __name__ == "__main__":
    example_usage()
