# Advanced LLM Intelligence - Implementation Plan

**Goal**: Add 4 high-impact LLM features to make Silicon-Pilot significantly more intelligent

---

## Feature #1: Intelligent Constraint Optimization  IMPLEMENTED

### Problem
Current constraint rules are static and may not be optimal for all use cases.

**Example**:
```yaml
rule: "if motor_type == BLDC"
  action: set pwm_timers = 3  # Is this always right?
```

### Solution: LLM-Optimized Constraints

**How It Works**:
1. Template provides baseline constraints
2. LLM analyzes user requirements + baseline
3. LLM suggests optimizations based on:
   - Domain knowledge (e.g., FOC algorithms need specific peripherals)
   - Best practices (e.g., safety margins)
   - Trade-offs (e.g., cost vs performance)
4. System applies optimized constraints

### Technical Approach

**File**: `architecture/intelligent_optimizer.py`

```python
class IntelligentConstraintOptimizer:
    """
    Uses LLM to optimize constraints beyond static rules.
    """
    
    def optimize_constraints(
        self,
        baseline_constraints: Dict[str, Any],
        user_requirements: Dict[str, Any],
        template_context: Dict[str, Any]
    ) -> OptimizationResult:
        """
        Optimize constraints using LLM reasoning.
        
        Returns:
            - optimized_constraints: Improved constraints
            - reasoning: Why each optimization was made
            - trade_offs: What was gained/lost
        """
        
        prompt = f"""
        Optimize these hardware constraints:
        
        Baseline (from template):
        {json.dumps(baseline_constraints, indent=2)}
        
        User Requirements:
        - Motor: {user_requirements['motor_type']}
        - Voltage: {user_requirements['supply_voltage']}
        - Current: {user_requirements['peak_current']}
        - Control: {user_requirements['control_mode']}
        
        Context:
        - Application: {template_context['device_type']}
        - Environment: {template_context.get('environment', 'unknown')}
        
        Analyze and suggest optimizations for:
        1. PWM timer configuration
        2. ADC channel allocation
        3. MCU speed requirements
        4. Memory requirements
        5. Peripheral selection
        
        Consider:
        - Algorithm requirements (e.g., FOC needs 6 PWM channels)
        - Safety margins (20% headroom recommended)
        - Real-world constraints (interrupt latency, DMA usage)
        - Cost vs performance trade-offs
        
        Respond with optimized constraints and reasoning.
        """
        
        # LLM call
        response = self.llm.chat(prompt)
        
        # Parse and validate
        optimizations = self._parse_optimizations(response)
        
        # Apply optimizations
        optimized = self._apply_optimizations(
            baseline_constraints,
            optimizations
        )
        
        return OptimizationResult(
            optimized_constraints=optimized,
            optimizations=optimizations,
            reasoning=response['reasoning']
        )
```

**Example Output**:
```json
{
  "optimizations": [
    {
      "field": "pwm_timers",
      "original": 3,
      "optimized": 1,
      "reasoning": "BLDC FOC needs 1 advanced timer with 6 channels (3 complementary pairs), not 3 separate timers. Use TIM1 with dead-time generation."
    },
    {
      "field": "min_mhz",
      "original": 168,
      "optimized": 180,
      "reasoning": "FOC at 20kHz PWM with current sensing needs ~150 MHz for algorithm + 20% margin for other tasks = 180 MHz minimum."
    },
    {
      "field": "adc_channels",
      "original": 3,
      "optimized": 4,
      "reasoning": "Need 3 for phase currents + 1 for DC bus voltage monitoring (safety requirement)."
    }
  ],
  "trade_offs": {
    "performance_gain": "Better motor control, faster response",
    "cost_impact": "Minimal - same MCU family",
    "complexity": "Slightly higher firmware complexity"
  }
}
```

---

## Feature #2: Context-Aware Component Selection

### Problem
Current selection is purely spec-based, ignoring user context.

**Example**: Recommending expensive H7 series for a student prototype.

### Solution: LLM Context Analysis

**How It Works**:
1. Gather user context (budget, expertise, project phase, timeline)
2. LLM analyzes top candidates with context
3. Re-ranks based on context-aware scoring
4. Provides context-specific reasoning

### Technical Approach

**File**: `solver/context_aware_selector.py`

```python
class ContextAwareSelector:
    """
    Selects components considering user context, not just specs.
    """
    
    def select_with_context(
        self,
        candidates: List[Component],
        requirements: RequirementSpec,
        user_context: UserContext
    ) -> ContextualRecommendation:
        """
        Re-rank candidates considering context.
        
        User Context includes:
        - project_phase: prototype/production/research
        - budget_sensitivity: low/medium/high
        - expertise_level: beginner/intermediate/expert
        - timeline: tight/normal/flexible
        - volume: units expected
        - support_needs: high/medium/low
        """
        
        prompt = f"""
        Select best MCU considering user context:
        
        Top Candidates (by specs):
        1. STM32F405RGT6 - $5.50, 168MHz, 1MB Flash
           - Pros: Popular, good docs, proven
           - Cons: Mid-range performance
        
        2. STM32H743VIT6 - $9.20, 480MHz, 2MB Flash
           - Pros: High performance, future-proof
           - Cons: 67% more expensive, complex
        
        3. STM32F103RBT6 - $3.50, 72MHz, 128KB Flash
           - Pros: Cheap, simple, widely available
           - Cons: Lower performance, less headroom
        
        User Context:
        - Phase: {user_context.project_phase}
        - Budget: {user_context.budget_sensitivity}
        - Expertise: {user_context.expertise_level}
        - Timeline: {user_context.timeline}
        - Volume: {user_context.expected_volume}
        
        Requirements:
        - Minimum specs: 168MHz, 256KB Flash, 2x CAN
        - Application: BLDC motor controller
        
        Which should we recommend FIRST? Consider:
        - Cost vs value for this project phase
        - Learning curve vs timeline
        - Community support for expertise level
        - Scalability for expected volume
        
        Rank all 3 with context-aware reasoning.
        """
        
        response = self.llm.chat(prompt)
        
        return ContextualRecommendation(
            primary=response['primary_choice'],
            alternatives=response['alternatives'],
            reasoning=response['reasoning'],
            context_factors=response['context_factors']
        )
```

**Example Output**:
```json
{
  "primary_choice": {
    "mpn": "STM32F405RGT6",
    "reasoning": "Best balance for prototype phase. Proven platform with extensive community support matches intermediate expertise level. $5.50 is reasonable for prototype budget. Sufficient performance headroom for BLDC control.",
    "context_match_score": 0.92
  },
  "alternatives": [
    {
      "mpn": "STM32F103RBT6",
      "reasoning": "If budget is extremely tight, this works but with minimal headroom. Risk: may need redesign for production.",
      "context_match_score": 0.65,
      "when_to_use": "Proof-of-concept only, not for production"
    },
    {
      "mpn": "STM32H743VIT6",
      "reasoning": "Overkill for prototype. Save this for production if you need advanced features or higher performance.",
      "context_match_score": 0.45,
      "when_to_use": "Production with demanding requirements"
    }
  ],
  "context_factors": {
    "budget_impact": "F405 is sweet spot - not cheapest but good value",
    "expertise_match": "F405 has best documentation and examples for intermediate users",
    "timeline_fit": "F405 has proven examples, faster development",
    "scalability": "F405 can scale to production if needed"
  }
}
```

---

## Feature #3: Smart Compatibility Checking

### Problem
Current compatibility checking is rule-based and misses subtle issues.

**Example**: Missing thermal issues, PCB layout concerns, or timing constraints.

### Solution: LLM Compatibility Analysis

**How It Works**:
1. Collect all BOM components
2. LLM analyzes multi-dimensional compatibility:
   - Electrical (voltage, current, timing)
   - Thermal (power dissipation, cooling)
   - Physical (package size, pin conflicts)
   - Software (driver compatibility, timing)
   - Manufacturing (assembly, availability)
3. Identifies issues with severity levels
4. Suggests fixes

### Technical Approach

**File**: `architecture/smart_compatibility.py`

```python
class SmartCompatibilityChecker:
    """
    Uses LLM to catch subtle compatibility issues.
    """
    
    def check_compatibility(
        self,
        bom: List[Component],
        architecture: ArchitectureGraph,
        constraints: Dict[str, Any]
    ) -> CompatibilityReport:
        """
        Deep compatibility analysis using LLM.
        
        Checks:
        - Electrical compatibility
        - Thermal compatibility
        - Timing compatibility
        - PCB layout concerns
        - Software/driver compatibility
        - Manufacturing concerns
        """
        
        prompt = f"""
        Analyze BOM compatibility for potential issues:
        
        Components:
        1. MCU: STM32F405RGT6
           - I/O: 3.3V, 5V tolerant
           - Power: 168MHz, ~150mA typical
           - Package: LQFP-64
           - Temp: -40 to 85°C
        
        2. CAN Transceiver: SN65HVD230
           - Supply: 3.3V
           - Current: 70mA max
           - Temp: -40 to 125°C
        
        3. Current Sensor: INA226
           - Supply: 2.7-5.5V
           - I2C interface
           - Current: 2mA
        
        4. Power Supply: TPS62160
           - Input: 3-17V
           - Output: 3.3V @ 1A
           - Efficiency: 95%
        
        5. Gate Driver: IR2104
           - Supply: 10-20V
           - Bootstrap supply needed
        
        Application: BLDC motor controller, 24V supply
        
        Check for issues in:
        
        1. ELECTRICAL:
           - Voltage level compatibility
           - Current budget (does 1A supply cover all?)
           - Power sequencing requirements
           - Pull-up/pull-down requirements
        
        2. THERMAL:
           - Power dissipation calculations
           - Cooling requirements
           - Thermal coupling between components
        
        3. TIMING:
           - I2C bus speed compatibility
           - CAN bus timing
           - PWM frequency limits
        
        4. PCB LAYOUT:
           - High-current traces for motor
           - Analog/digital separation
           - EMI concerns
           - Component placement
        
        5. SOFTWARE:
           - Driver availability
           - DMA channel conflicts
           - Interrupt priority conflicts
        
        6. MANUFACTURING:
           - Component availability
           - Assembly complexity
           - Test points needed
        
        Identify issues with severity (CRITICAL/WARNING/INFO) and suggest fixes.
        """
        
        response = self.llm.chat(prompt)
        
        return CompatibilityReport(
            issues=response['issues'],
            suggestions=response['suggestions'],
            overall_status=response['status']
        )
```

**Example Output**:
```json
{
  "issues": [
    {
      "severity": "WARNING",
      "category": "ELECTRICAL",
      "component": "Power Supply TPS62160",
      "issue": "Current budget is tight",
      "analysis": "MCU: 150mA + CAN: 70mA + Sensor: 2mA + Gate Driver: 15mA = 237mA typical. With 20% margin = 284mA. 1A supply is OK but only 3.5x margin. Recommend 1.5A for better margin.",
      "suggestion": "Use TPS62162 (1.5A) for better margin, only $0.10 more"
    },
    {
      "severity": "CRITICAL",
      "category": "ELECTRICAL",
      "component": "Gate Driver IR2104",
      "issue": "Bootstrap supply not in BOM",
      "analysis": "IR2104 needs bootstrap capacitor and diode for high-side drive. Missing from BOM.",
      "suggestion": "Add: 1x 10µF/25V bootstrap cap, 1x fast diode (e.g., 1N4148)"
    },
    {
      "severity": "INFO",
      "category": "PCB_LAYOUT",
      "issue": "CAN termination resistor placement",
      "analysis": "CAN termination should be close to transceiver to minimize stub length.",
      "suggestion": "Place 120Ω resistor within 5mm of SN65HVD230"
    },
    {
      "severity": "WARNING",
      "category": "THERMAL",
      "issue": "Gate driver power dissipation",
      "analysis": "At 20kHz PWM with 10A load, gate driver dissipates ~0.5W. SOIC-8 package needs good thermal relief.",
      "suggestion": "Add thermal vias under IR2104, or use larger package (DIP-8)"
    }
  ],
  "overall_status": "COMPATIBLE_WITH_CHANGES",
  "summary": "1 critical issue (missing bootstrap components), 2 warnings (power budget, thermal). Fix critical issue before proceeding."
}
```

---

## Feature #4: LLM-Driven Configuration Generation

### Problem
MCU configuration is complex with many interdependencies.

**Example**: Clock tree, pin muxing, DMA channels, interrupt priorities.

### Solution: LLM Configuration Expert

**How It Works**:
1. LLM analyzes requirements + MCU capabilities
2. Generates optimal configuration considering:
   - Clock tree optimization
   - Pin conflict resolution
   - DMA channel allocation
   - Interrupt priority assignment
   - Power optimization
3. Outputs STM32CubeMX .ioc file or code

### Technical Approach

**File**: `architecture/config_generator.py`

```python
class LLMConfigGenerator:
    """
    Generates optimal MCU configuration using LLM expertise.
    """
    
    def generate_config(
        self,
        mcu: Component,
        requirements: RequirementSpec,
        peripherals_needed: Dict[str, Any]
    ) -> MCUConfiguration:
        """
        Generate complete MCU configuration.
        
        Generates:
        - Clock tree configuration
        - Pin assignments
        - DMA channel allocation
        - Interrupt priorities
        - Power mode settings
        """
        
        prompt = f"""
        Generate optimal STM32F405 configuration:
        
        Requirements:
        - 3-phase BLDC motor control (FOC algorithm)
        - PWM frequency: 20kHz
        - Current sensing: 3 phases + DC bus
        - CAN communication: 500kbps
        - USB for debugging
        - Quadrature encoder input
        
        Peripherals Needed:
        - 1x Advanced Timer (6 PWM channels with complementary)
        - 3x ADC channels (current sensing)
        - 2x CAN controllers
        - 1x USB
        - 1x Timer for encoder
        - 2x UART (debug + expansion)
        
        Generate configuration for:
        
        1. CLOCK TREE:
           - HSE frequency
           - PLL configuration for 168MHz
           - APB1/APB2 dividers
           - USB clock (must be 48MHz)
           - Optimize for:
             * PWM timer on APB2 (higher freq better)
             * CAN on APB1 (max 42MHz)
             * USB needs exact 48MHz
        
        2. PIN ASSIGNMENTS:
           - TIM1 for motor PWM (6 channels)
           - ADC1/2/3 for current sensing
           - CAN1/CAN2 pins
           - USB pins
           - TIM3 for encoder
           - Minimize conflicts
           - Group related pins for easier routing
        
        3. DMA CHANNELS:
           - ADC → DMA (for current sampling)
           - UART → DMA (for debug)
           - Avoid conflicts
        
        4. INTERRUPT PRIORITIES:
           - Highest: ADC (current sensing - safety critical)
           - High: TIM1 update (PWM timing)
           - Medium: CAN RX
           - Low: UART, USB
        
        5. POWER OPTIMIZATION:
           - Which peripherals can sleep?
           - Clock gating opportunities
        
        Output as STM32CubeMX-compatible configuration.
        """
        
        response = self.llm.chat(prompt)
        
        # Parse and validate configuration
        config = self._parse_config(response)
        
        # Validate no conflicts
        validation = self._validate_config(config, mcu)
        
        if not validation.is_valid:
            # LLM fixes conflicts
            config = self._fix_conflicts(config, validation.conflicts)
        
        return MCUConfiguration(
            clock_tree=config['clock'],
            pin_assignments=config['pins'],
            dma_channels=config['dma'],
            interrupt_priorities=config['interrupts'],
            power_settings=config['power'],
            reasoning=response['reasoning']
        )
```

**Example Output**:
```json
{
  "clock_tree": {
    "hse_mhz": 8,
    "pll_m": 8,
    "pll_n": 336,
    "pll_p": 2,
    "pll_q": 7,
    "sysclk_mhz": 168,
    "ahb_div": 1,
    "apb1_div": 4,
    "apb2_div": 2,
    "apb1_mhz": 42,
    "apb2_mhz": 84,
    "usb_clk_mhz": 48,
    "reasoning": "APB2 at 84MHz gives TIM1 168MHz (2x multiplier), perfect for 20kHz PWM. APB1 at 42MHz is max for CAN. USB gets exact 48MHz from PLL_Q."
  },
  "pin_assignments": {
    "TIM1_CH1": "PA8",
    "TIM1_CH1N": "PA7",
    "TIM1_CH2": "PA9",
    "TIM1_CH2N": "PB0",
    "TIM1_CH3": "PA10",
    "TIM1_CH3N": "PB1",
    "ADC1_IN0": "PA0",
    "ADC1_IN1": "PA1",
    "ADC1_IN2": "PA2",
    "ADC1_IN3": "PA3",
    "CAN1_RX": "PD0",
    "CAN1_TX": "PD1",
    "USB_DM": "PA11",
    "USB_DP": "PA12",
    "reasoning": "TIM1 channels grouped on Port A/B for easier routing. ADC inputs on PA0-3 (consecutive). CAN on PD to avoid conflicts."
  },
  "dma_channels": {
    "ADC1": "DMA2_Stream0_Channel0",
    "UART1_TX": "DMA2_Stream7_Channel4",
    "reasoning": "ADC on DMA2 for best performance. No conflicts."
  },
  "interrupt_priorities": {
    "ADC1": {"preempt": 0, "sub": 0, "reasoning": "Highest - safety critical current sensing"},
    "TIM1_UP": {"preempt": 1, "sub": 0, "reasoning": "High - PWM timing"},
    "CAN1_RX": {"preempt": 2, "sub": 0, "reasoning": "Medium - communication"},
    "UART1": {"preempt": 3, "sub": 0, "reasoning": "Low - debug only"}
  }
}
```

---

## Integration Strategy

### Phase 1: Implement Core LLM Modules (Week 1)
- [x] Create `architecture/intelligent_optimizer.py`
- [ ] Create `solver/context_aware_selector.py`
- [ ] Create `architecture/smart_compatibility.py`
- [ ] Create `architecture/config_generator.py`

### Phase 2: Integrate with Existing Pipeline (Week 2)
- [ ] Add optimizer to Architecture Compiler
- [ ] Add context-aware selection to Subsystem Solvers
- [ ] Add compatibility checking to BOM Composer
- [ ] Add config generation to Export Manager

### Phase 3: Testing & Refinement (Week 3)
- [ ] Test each feature independently
- [ ] Test integrated pipeline
- [ ] Gather user feedback
- [ ] Refine prompts based on results

### Phase 4: Production Deployment (Week 4)
- [ ] Performance optimization
- [ ] Error handling
- [ ] Documentation
- [ ] Deploy to production

---

## Success Metrics

### Feature #1: Intelligent Constraint Optimization
- **Metric**: % of constraints improved by LLM
- **Target**: 30%+ of cases show measurable improvement
- **Validation**: Expert review of optimizations

### Feature #2: Context-Aware Selection
- **Metric**: User satisfaction with recommendations
- **Target**: 85%+ users agree recommendation fits their context
- **Validation**: User surveys

### Feature #3: Smart Compatibility Checking
- **Metric**: Issues caught that rules missed
- **Target**: Find 5+ issues per 100 BOMs that rules missed
- **Validation**: Expert review

### Feature #4: LLM Configuration Generation
- **Metric**: Configuration correctness
- **Target**: 95%+ configurations compile without errors
- **Validation**: STM32CubeMX validation

---

## Risk Mitigation

### Risk #1: LLM Hallucination
**Mitigation**: Always validate LLM output against:
- MCU datasheet constraints
- Electrical rules
- Known good configurations

### Risk #2: Performance
**Mitigation**: 
- Cache LLM responses
- Use async processing
- Provide "quick mode" (skip LLM)

### Risk #3: Cost
**Mitigation**:
- Use GPT-4-mini for simpler tasks
- Batch requests when possible
- Implement request limits

---

## Next Steps

1. **Implement Feature #1** (Intelligent Constraint Optimization) - Highest impact, easiest to validate
2. **Implement Feature #3** (Smart Compatibility Checking) - High value, clear success criteria
3. **Implement Feature #2** (Context-Aware Selection) - Requires user context collection
4. **Implement Feature #4** (LLM Configuration Generation) - Most complex, highest value

**Ready to start implementation?**
