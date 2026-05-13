"""
Intent Classifier for HardwareGenius Phase 2

Uses LLM to parse user natural language and extract:
- Device type
- Keywords
- Domain-specific parameters
- Matched templates

The LLM is used ONLY for classification, NOT for design decisions.
"""
from __future__ import annotations
import os
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import json

from core.ontology import DeviceType, InterfaceType, EnvironmentType
from templates.template_system import TemplateLoader, DeviceTemplate
import core.llm_config as llm_cfg

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================================
# Intent Models
# ============================================================================

class ExtractedIntent(BaseModel):
    """Parsed user intent"""
    device_type: Optional[DeviceType] = None
    keywords: List[str] = Field(default_factory=list)
    extracted_params: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""


class TemplateMatch(BaseModel):
    """A matched template with score"""
    template_id: str
    template_name: str
    score: float
    match_reasons: List[str] = Field(default_factory=list)


# ============================================================================
# Intent Classifier
# ============================================================================

class IntentParser:
    """
    Classifies user intent using LLM.
    
    Extracts:
    - Device type
    - Keywords
    - Domain-specific parameters
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str | None = None, use_llm: bool = True):
        self.model = model or llm_cfg.MODEL_PARSER
        # Always build client from central config (points to Ollama by default)
        self.client = llm_cfg.get_openai_client() if use_llm else None
    
    def classify(self, user_input: str) -> ExtractedIntent:
        """
        Classify user intent from natural language.
        
        Args:
            user_input: User's natural language description
            
        Returns:
            ExtractedIntent with device type, keywords, and parameters
        """
        if not self.client:
            # Fallback to keyword-based classification
            return self._fallback_classify(user_input)
        
        # Build LLM prompt
        prompt = self._build_classification_prompt(user_input)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent classification
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            return ExtractedIntent(
                device_type=DeviceType(result.get("device_type")) if result.get("device_type") else None,
                keywords=result.get("keywords", []),
                extracted_params=result.get("extracted_params", {}),
                confidence=result.get("confidence", 0.0),
                reasoning=result.get("reasoning", "")
            )
            
        except Exception as e:
            print(f"LLM classification failed: {e}, falling back to keyword-based")
            return self._fallback_classify(user_input)
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        device_types = [dt.value for dt in DeviceType]
        
        return f"""You are an expert hardware engineer assistant. Your task is to classify user intent for hardware design.

Extract the following from user input:
1. device_type: One of {device_types}
2. keywords: List of relevant technical keywords
3. extracted_params: Dict of specific parameters mentioned (e.g., voltage, current, protocols)
4. confidence: 0.0-1.0 confidence score
5. reasoning: Brief explanation of classification

Respond ONLY with valid JSON matching this schema:
{{
    "device_type": "sensor_node",
    "keywords": ["temperature", "wireless", "battery"],
    "extracted_params": {{
        "wireless_protocol": "lora",
        "battery_powered": true,
        "sensors": ["temperature", "humidity"]
    }},
    "confidence": 0.9,
    "reasoning": "User wants battery-powered wireless sensor"
}}

Be conservative with confidence scores. If unsure, set confidence < 0.5."""
    
    def _build_classification_prompt(self, user_input: str) -> str:
        """Build classification prompt"""
        return f"""Classify this hardware design intent:

"{user_input}"

Extract device type, keywords, and parameters."""
    
    def _fallback_classify(self, user_input: str) -> ExtractedIntent:
        """Fallback keyword-based classification"""
        user_lower = user_input.lower()
        keywords = []
        extracted_params = {}
        device_type = None
        
        # Device type keywords
        device_keywords = {
            DeviceType.MOTOR_CONTROLLER: ["motor", "controller", "bldc", "servo", "actuator", "drive"],
            DeviceType.SENSOR_NODE: ["sensor", "monitoring", "iot", "wireless", "environmental"],
            DeviceType.DATA_LOGGER: ["logger", "logging", "data", "acquisition", "recording"],
            DeviceType.GATEWAY: ["gateway", "bridge", "router", "hub"],
            DeviceType.WEARABLE: ["wearable", "watch", "fitness", "tracker"],
        }
        
        # Match device type
        for dtype, kws in device_keywords.items():
            if any(kw in user_lower for kw in kws):
                device_type = dtype
                keywords.extend([kw for kw in kws if kw in user_lower])
                break
        
        # Extract interface keywords
        interface_keywords = {
            "can": "can",
            "usb": "usb",
            "ethernet": "ethernet",
            "wifi": "wifi",
            "bluetooth": "bluetooth",
            "ble": "ble",
            "lora": "lora",
            "i2c": "i2c",
            "spi": "spi",
        }
        
        for kw, param in interface_keywords.items():
            if kw in user_lower:
                keywords.append(kw)
                extracted_params[f"{param}_required"] = True
        
        # Extract power keywords
        if "battery" in user_lower or "portable" in user_lower:
            keywords.append("battery")
            extracted_params["battery_powered"] = True
        
        if "solar" in user_lower:
            keywords.append("solar")
            extracted_params["solar_powered"] = True
        
        # Extract environment keywords
        if "automotive" in user_lower:
            keywords.append("automotive")
            extracted_params["environment"] = "automotive"
        elif "industrial" in user_lower:
            keywords.append("industrial")
            extracted_params["environment"] = "industrial"
        
        confidence = 0.6 if device_type else 0.3
        
        return ExtractedIntent(
            device_type=device_type,
            keywords=list(set(keywords)),
            extracted_params=extracted_params,
            confidence=confidence,
            reasoning="Keyword-based classification (LLM unavailable)"
        )


# ============================================================================
# Template Matcher
# ============================================================================

class TemplateMatcher:
    """
    Deterministic template matching based on intent.
    
    NOT LLM-based - uses keyword scoring and device type matching.
    """
    
    def __init__(self, template_loader: TemplateLoader):
        self.loader = template_loader
    
    def match_templates(
        self,
        intent: ExtractedIntent,
        top_k: int = 5
    ) -> List[TemplateMatch]:
        """
        Match templates to user intent.
        
        Args:
            intent: Extracted user intent
            top_k: Number of top matches to return
            
        Returns:
            List of TemplateMatch sorted by score (descending)
        """
        matches = []
        
        for template in self.loader.list_all_templates():
            score, reasons = self._score_template(template, intent)
            
            if score > 0:
                matches.append(TemplateMatch(
                    template_id=template.id,
                    template_name=template.name,
                    score=score,
                    match_reasons=reasons
                ))
        
        # Sort by score descending
        matches.sort(key=lambda x: x.score, reverse=True)
        
        return matches[:top_k]
    
    def _score_template(
        self,
        template: DeviceTemplate,
        intent: ExtractedIntent
    ) -> tuple[float, List[str]]:
        """
        Score a template against intent.
        
        Returns:
            (score, list_of_reasons)
        """
        score = 0.0
        reasons = []
        
        # Device type match (highest weight)
        if intent.device_type and template.device_type == intent.device_type:
            score += 50.0
            reasons.append(f"Device type match: {intent.device_type.value}")
        
        # Keyword matching in tags
        keyword_matches = 0
        for keyword in intent.keywords:
            if any(keyword.lower() in tag.lower() for tag in template.tags):
                keyword_matches += 1
                score += 5.0
        
        if keyword_matches > 0:
            reasons.append(f"{keyword_matches} keyword matches in tags")
        
        # Keyword matching in name/description
        for keyword in intent.keywords:
            if (keyword.lower() in template.name.lower() or
                keyword.lower() in template.description.lower()):
                score += 3.0
                keyword_matches += 1
        
        # Parameter matching
        param_matches = 0
        for param_key, param_value in intent.extracted_params.items():
            # Check if template questions ask about this parameter
            for question in template.questions:
                if param_key.lower() in question.id.lower() or param_key.lower() in question.text.lower():
                    score += 2.0
                    param_matches += 1
                    break
        
        if param_matches > 0:
            reasons.append(f"{param_matches} parameter matches")
        
        # Normalize score
        max_possible_score = 50.0 + len(intent.keywords) * 8.0 + len(intent.extracted_params) * 2.0
        if max_possible_score > 0:
            score = (score / max_possible_score) * 100.0
        
        return score, reasons
    
    def get_best_match(self, intent: ExtractedIntent) -> Optional[DeviceTemplate]:
        """Get single best matching template"""
        matches = self.match_templates(intent, top_k=1)
        
        if matches and matches[0].score > 30.0:  # Minimum confidence threshold
            return self.loader.get_template(matches[0].template_id)
        
        return None


# ============================================================================
# Combined Intent Pipeline
# ============================================================================

class IntentPipeline:
    """Complete intent classification and template matching pipeline"""
    
    def __init__(
        self,
        template_loader: TemplateLoader,
        api_key: Optional[str] = None,
        model: str = "gpt-4"
    ):
        self.classifier = IntentParser(api_key=api_key, model=model)
        self.matcher = TemplateMatcher(template_loader)
    
    def process(self, user_input: str, top_k: int = 5) -> tuple[ExtractedIntent, List[TemplateMatch]]:
        """
        Process user input through full pipeline.
        
        Args:
            user_input: User's natural language description
            top_k: Number of template matches to return
            
        Returns:
            (intent, template_matches)
        """
        # Step 1: Classify intent
        intent = self.classifier.classify(user_input)
        
        # Step 2: Match templates
        matches = self.matcher.match_templates(intent, top_k=top_k)
        
        return intent, matches
