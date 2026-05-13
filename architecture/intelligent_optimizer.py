"""
Intelligent Constraint Optimizer

Uses LLM to optimize constraints beyond static template rules.
Analyzes user requirements and suggests improvements based on:
- Domain knowledge
- Best practices
- Trade-offs
- Safety margins
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import json
import os
import core.llm_config as llm_cfg


# ============================================================================
# Models
# ============================================================================

class ConstraintOptimization(BaseModel):
    """Single constraint optimization"""
    field: str
    original_value: Any
    optimized_value: Any
    reasoning: str
    impact: str  # performance/cost/safety/complexity
    confidence: float  # 0.0-1.0


class OptimizationResult(BaseModel):
    """Result of constraint optimization"""
    optimized_constraints: Dict[str, Any]
    optimizations: List[ConstraintOptimization]
    trade_offs: Dict[str, str]
    overall_reasoning: str
    confidence_score: float


# ============================================================================
# Intelligent Constraint Optimizer
# ============================================================================

class IntelligentConstraintOptimizer:
    """
    LLM-driven constraint optimizer.
    
    Improves baseline constraints from templates by:
    1. Analyzing user requirements
    2. Applying domain knowledge
    3. Considering best practices
    4. Balancing trade-offs
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str | None = None):
        self.model = model or llm_cfg.MODEL_PARSER
        self.client = llm_cfg.get_openai_client()
    
    def optimize_constraints(
        self,
        baseline_constraints: Dict[str, Any],
        user_requirements: Dict[str, Any],
        template_context: Dict[str, Any]
    ) -> OptimizationResult:
        """
        Optimize constraints using LLM reasoning.
        
        Args:
            baseline_constraints: Constraints from template
            user_requirements: User's specific requirements
            template_context: Template metadata and context
            
        Returns:
            OptimizationResult with improved constraints
        """
        
        if not self.client:
            # Fallback: return baseline unchanged
            return self._fallback_optimization(baseline_constraints)
        
        # Build optimization prompt
        prompt = self._build_optimization_prompt(
            baseline_constraints,
            user_requirements,
            template_context
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,  # Low temperature for consistent optimization
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse optimizations
            optimizations = []
            for opt in result.get("optimizations", []):
                optimizations.append(ConstraintOptimization(
                    field=opt["field"],
                    original_value=opt["original_value"],
                    optimized_value=opt["optimized_value"],
                    reasoning=opt["reasoning"],
                    impact=opt["impact"],
                    confidence=opt.get("confidence", 0.8)
                ))
            
            # Apply optimizations to baseline
            optimized = self._apply_optimizations(
                baseline_constraints,
                optimizations
            )
            
            return OptimizationResult(
                optimized_constraints=optimized,
                optimizations=optimizations,
                trade_offs=result.get("trade_offs", {}),
                overall_reasoning=result.get("overall_reasoning", ""),
                confidence_score=result.get("confidence_score", 0.8)
            )
            
        except Exception as e:
            print(f"LLM optimization failed: {e}")
            return self._fallback_optimization(baseline_constraints)
    
    def _get_system_prompt(self) -> str:
        """System prompt for constraint optimization"""
        return """You are an expert hardware engineer specializing in embedded systems design. Your task is to optimize hardware constraints for better designs.

Analyze baseline constraints and suggest improvements based on:

1. **Domain Knowledge**:
   - Algorithm requirements (e.g., FOC needs specific peripherals)
   - Industry best practices
   - Common pitfalls and how to avoid them

2. **Safety Margins**:
   - 20% headroom for memory/processing
   - Thermal margins
   - Current/voltage margins

3. **Trade-offs**:
   - Performance vs cost
   - Complexity vs reliability
   - Power vs speed

4. **Real-world Constraints**:
   - Interrupt latency
   - DMA bandwidth
   - Bus speeds
   - Timing requirements

For each optimization, provide:
- Field name
- Original value
- Optimized value
- Clear reasoning
- Impact category (performance/cost/safety/complexity)
- Confidence (0.0-1.0)

Respond with JSON:
{
    "optimizations": [
        {
            "field": "pwm_timers",
            "original_value": 3,
            "optimized_value": 1,
            "reasoning": "BLDC FOC needs 1 advanced timer with 6 channels (3 complementary pairs), not 3 separate timers",
            "impact": "performance",
            "confidence": 0.95
        }
    ],
    "trade_offs": {
        "performance": "Better motor control",
        "complexity": "Slightly higher firmware complexity"
    },
    "overall_reasoning": "Optimizations focus on correct peripheral usage and safety margins",
    "confidence_score": 0.9
}

Only suggest optimizations that are clearly beneficial. If baseline is already optimal, return empty optimizations list."""
    
    def _build_optimization_prompt(
        self,
        baseline: Dict[str, Any],
        requirements: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Build optimization prompt"""
        
        prompt = f"""Optimize these hardware constraints:

BASELINE CONSTRAINTS (from template):
{json.dumps(baseline, indent=2)}

USER REQUIREMENTS:
{json.dumps(requirements, indent=2)}

CONTEXT:
- Device Type: {context.get('device_type', 'unknown')}
- Application: {context.get('application', 'unknown')}
- Environment: {context.get('environment', 'unknown')}

Analyze and suggest optimizations for:
1. Peripheral configuration (timers, ADC, DMA, etc.)
2. Memory requirements (Flash, RAM)
3. Processing requirements (CPU speed)
4. Interface requirements (CAN, USB, etc.)
5. Safety margins

Consider:
- Algorithm requirements (e.g., FOC, PID, filtering)
- Real-time constraints
- Safety margins (20% recommended)
- Cost vs performance trade-offs
- Complexity vs reliability

Suggest optimizations that improve the design."""
        
        return prompt
    
    def _apply_optimizations(
        self,
        baseline: Dict[str, Any],
        optimizations: List[ConstraintOptimization]
    ) -> Dict[str, Any]:
        """Apply optimizations to baseline constraints"""
        
        optimized = baseline.copy()
        
        for opt in optimizations:
            # Navigate nested fields (e.g., "peripherals.pwm_timers")
            field_parts = opt.field.split('.')
            target = optimized
            
            for part in field_parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            
            final_field = field_parts[-1]
            target[final_field] = opt.optimized_value
        
        return optimized
    
    def _fallback_optimization(
        self,
        baseline: Dict[str, Any]
    ) -> OptimizationResult:
        """Fallback when LLM unavailable"""
        
        return OptimizationResult(
            optimized_constraints=baseline,
            optimizations=[],
            trade_offs={},
            overall_reasoning="LLM unavailable, using baseline constraints",
            confidence_score=0.5
        )


# ============================================================================
# Constraint Validator
# ============================================================================

class ConstraintValidator:
    """
    Validates optimized constraints against MCU capabilities.
    
    Ensures LLM suggestions are physically possible.
    """
    
    def validate_constraints(
        self,
        constraints: Dict[str, Any],
        mcu_capabilities: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, List[str]]:
        """
        Validate constraints are achievable.
        
        Returns:
            (is_valid, list_of_issues)
        """
        
        issues = []
        
        # Check memory constraints
        if "min_flash_kb" in constraints:
            if constraints["min_flash_kb"] > 2048:  # Reasonable max
                issues.append(f"Flash requirement {constraints['min_flash_kb']}KB is very high")
        
        if "min_sram_kb" in constraints:
            if constraints["min_sram_kb"] > 512:  # Reasonable max
                issues.append(f"SRAM requirement {constraints['min_sram_kb']}KB is very high")
        
        # Check peripheral counts
        peripherals = constraints.get("peripherals_min", {})
        
        if peripherals.get("can", 0) > 3:
            issues.append("CAN count > 3 is unusual for single MCU")
        
        if peripherals.get("uart", 0) > 8:
            issues.append("UART count > 8 is unusual")
        
        # Check clock speed
        if "min_mhz" in constraints:
            if constraints["min_mhz"] > 600:
                issues.append(f"Clock speed {constraints['min_mhz']}MHz is very high")
        
        return len(issues) == 0, issues


# ============================================================================
# Example Usage
# ============================================================================

def example_usage():
    """Demonstrate intelligent constraint optimization"""
    
    # Baseline constraints from template
    baseline = {
        "core_arch": "cortex-m4",
        "min_flash_kb": 256,
        "min_sram_kb": 64,
        "min_mhz": 168,
        "peripherals_min": {
            "can": 2,
            "pwm_timers": 3,  # This will be optimized
            "adc_channels": 3,
            "uart": 2
        },
        "has_fpu": True
    }
    
    # User requirements
    requirements = {
        "motor_type": "BLDC",
        "supply_voltage": "24V",
        "peak_current": "10A",
        "control_mode": "Closed-loop (FOC)",
        "pwm_frequency": "20kHz"
    }
    
    # Template context
    context = {
        "device_type": "motor_controller",
        "application": "BLDC motor control",
        "environment": "industrial"
    }
    
    # Create optimizer
    optimizer = IntelligentConstraintOptimizer()
    
    # Optimize constraints
    result = optimizer.optimize_constraints(
        baseline_constraints=baseline,
        user_requirements=requirements,
        template_context=context
    )
    
    # Display results
    print("=" * 80)
    print("INTELLIGENT CONSTRAINT OPTIMIZATION")
    print("=" * 80)
    print()
    
    print("OPTIMIZATIONS:")
    for opt in result.optimizations:
        print(f"\n  {opt.field}:")
        print(f"    Original: {opt.original_value}")
        print(f"    Optimized: {opt.optimized_value}")
        print(f"    Reasoning: {opt.reasoning}")
        print(f"    Impact: {opt.impact}")
        print(f"    Confidence: {opt.confidence:.0%}")
    
    print(f"\nOVERALL REASONING:")
    print(f"  {result.overall_reasoning}")
    
    print(f"\nTRADE-OFFS:")
    for key, value in result.trade_offs.items():
        print(f"  {key}: {value}")
    
    print(f"\nCONFIDENCE SCORE: {result.confidence_score:.0%}")
    
    # Validate optimized constraints
    validator = ConstraintValidator()
    is_valid, issues = validator.validate_constraints(result.optimized_constraints)
    
    print(f"\nVALIDATION: {'✅ PASS' if is_valid else '❌ FAIL'}")
    if issues:
        print("  Issues:")
        for issue in issues:
            print(f"    - {issue}")


if __name__ == "__main__":
    example_usage()
