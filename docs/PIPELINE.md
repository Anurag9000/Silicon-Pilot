# HardwareGenius Pipeline - Visual Explanation

**Understanding the Core Components**

---

## 🔄 The Complete Pipeline

```
User Input
    ↓
[1] Intent Classification (LLM)
    ↓
[2] Template Matching (Deterministic)
    ↓
[3] Dynamic Questioning (LLM) ← NEW!
    ↓
[4] Architecture Compiler (Deterministic)
    ↓
[5] Subsystem Solvers (Deterministic)
    ↓
[6] BOM Composer (Deterministic)
    ↓
[7] Configuration Generator (Deterministic)
    ↓
[8] Export Manager (Deterministic)
    ↓
Final Output (BOM + Config + CAD Files)
```

---

## 📐 Component #4: Architecture Compiler

### What It Does

**Transforms** high-level template + user answers → **low-level technical constraints**

### Visual Example

**Input** (Template + Answers):
```yaml
Template: CAN Motor Controller
Answers:
  motor_type: BLDC
  supply_voltage: 24V
  peak_current: 10A
  control_mode: Closed-loop
```

**Architecture Compiler Process**:
```
Step 1: Build Architecture Graph
├── Subsystem: Compute
│   ├── Functions: [motor_control, can_communication, sensing]
│   └── Baseline: {core: cortex-m4, flash: 256KB, ram: 64KB}
│
├── Subsystem: Power
│   ├── Functions: [voltage_regulation]
│   └── Baseline: {input: 24V, output: 3.3V, current: 1A}
│
├── Subsystem: Motor Control
│   ├── Functions: [pwm_generation, current_sensing]
│   └── Baseline: {pwm_channels: 3, adc_channels: 3}
│
└── Subsystem: Communication
    ├── Functions: [can_transceiver]
    └── Baseline: {protocol: CAN, bitrate: 500kbps}

Step 2: Apply Rules Based on Answers
Rule: "If motor_type == BLDC"
  → Update compute.peripherals.pwm_timers = 3
  → Update compute.peripherals.adc_channels = 3
  → Add motor_control subsystem

Rule: "If control_mode == Closed-loop"
  → Update compute.peripherals.encoder_interface = 1
  → Increase compute.min_mhz = 168

Step 3: Compile to RequirementSpec
Output:
{
  "core_arch": "cortex-m4",
  "min_flash_kb": 256,
  "min_sram_kb": 64,
  "min_mhz": 168,
  "peripherals_min": {
    "can": 2,
    "pwm_timers": 3,
    "adc_channels": 3,
    "encoder_interface": 1,
    "uart": 2
  },
  "temp_min": -40,
  "temp_max": 85,
  "package_family": "LQFP"
}
```

**Output**: `RequirementSpec` - Machine-readable constraints for solvers

---

## 🔧 Component #5: Subsystem Solvers

### What They Do

**Find actual components** that satisfy the constraints from Architecture Compiler

### The 7 Solvers

```
1. MCU Solver (Compute Subsystem)
   ├── Input: core_arch, flash, ram, peripherals
   └── Output: STM32F405RGT6 ($5.50)

2. Power Solver (Power Subsystem)
   ├── Input: input_voltage, output_voltage, current
   └── Output: TPS62160 ($1.20)

3. Transceiver Solver (Communication Subsystem)
   ├── Input: protocol, bitrate
   └── Output: SN65HVD230 ($0.60)

4. Sensor Solver (Sensing Subsystem)
   ├── Input: sensor_types, interfaces
   └── Output: Temperature/Current sensors

5. Memory Solver (Storage Subsystem)
   ├── Input: capacity, interface, type
   └── Output: Flash/EEPROM chips

6. Display Solver (UI Subsystem)
   ├── Input: resolution, interface, size
   └── Output: LCD/OLED displays

7. Protection Solver (Protection Subsystem)
   ├── Input: voltage, current, protection_type
   └── Output: TVS diodes, fuses
```

### How a Solver Works (MCU Example)

```python
# Step 1: Hard Filter (Deterministic)
candidates = database.query("""
    SELECT * FROM mcu_specs
    WHERE core = 'cortex-m4'
      AND flash_kb >= 256
      AND sram_kb >= 64
      AND can_count >= 2
      AND pwm_timers >= 3
      AND status = 'active'
""")
# Result: 47 MCUs match

# Step 2: Rank by Score (Deterministic)
for mcu in candidates:
    score = 0
    
    # Headroom (more is better, but diminishing returns)
    flash_headroom = (mcu.flash_kb - 256) / 256
    score += min(flash_headroom * 20, 30)  # Max 30 points
    
    # Peripheral margin
    extra_pwm = mcu.pwm_timers - 3
    score += extra_pwm * 5  # 5 points per extra
    
    # Ecosystem (curated score)
    score += mcu.ecosystem_score  # 0-20 points
    
    # Availability
    if mcu.stock > 1000:
        score += 10
    
    mcu.total_score = score

# Step 3: Sort and Return Top 10
top_mcus = sorted(candidates, key=lambda x: x.total_score, reverse=True)[:10]

# Result:
# 1. STM32F405RGT6 (score: 87) - $5.50
# 2. STM32F407VGT6 (score: 85) - $6.20
# 3. STM32F446RET6 (score: 82) - $5.80
```

### Evidence Tracking

Every recommendation includes **proof**:
```json
{
  "mpn": "STM32F405RGT6",
  "evidence": [
    {
      "field": "flash_kb",
      "value": 1024,
      "source": "https://st.com/stm32f405.pdf",
      "page": 12,
      "snippet": "1 Mbyte of Flash memory"
    },
    {
      "field": "can_count",
      "value": 2,
      "source": "https://st.com/stm32f405.pdf",
      "page": 15,
      "snippet": "2× CAN 2.0B interfaces"
    }
  ]
}
```

---

## 🎯 Component #6: BOM Composer

### What It Does

**Assembles** components from all subsystem solvers into a **complete, compatible BOM**

### The Process

```
Input: Recommendations from 7 solvers

Step 1: Collect Components
├── MCU: STM32F405RGT6
├── Power: TPS62160
├── CAN Transceiver: SN65HVD230
├── Current Sensor: INA226
├── Protection: SMBJ24A (x2)
└── Connectors: USB-C, CAN terminal

Step 2: Compatibility Checking
✓ MCU voltage (3.3V) matches CAN transceiver (3.3V)
✓ MCU I2C available for current sensor
✓ Power supply output (3.3V/1A) sufficient for all components
✓ Protection voltage (24V) matches supply voltage
✗ WARNING: MCU has only 1 USB, but template requires USB + debug
  → Add: ST-LINK debugger

Step 3: Add Passive Components
├── Decoupling caps for MCU (10x 100nF, 3x 10µF)
├── Decoupling caps for power (2x 22µF)
├── CAN termination resistor (120Ω)
├── Pull-up resistors for I2C (2x 4.7kΩ)
└── LED indicators (3x LED + resistors)

Step 4: Calculate Totals
├── Component count: 23
├── Unique parts: 15
├── Total cost: $8.47
└── Total power: 0.45W @ 3.3V

Step 5: Generate Alternatives
Alternative 1: Lower cost
  - Replace STM32F405 → STM32F103 (save $2.00)
  - Total: $6.47

Alternative 2: Higher performance
  - Replace STM32F405 → STM32H743 (add $3.50)
  - Total: $11.97
```

**Output**: Complete BOM with alternatives and compatibility notes

---

## 🤖 Where We Can Add MORE LLM Intelligence

### Current State (Deterministic vs LLM)

| Component | Current | LLM Potential |
|-----------|---------|---------------|
| Intent Classification | ✅ LLM | Already using |
| Template Matching | ❌ Keyword | 🎯 Can improve |
| Dynamic Questioning | ✅ LLM | Already using |
| Architecture Compiler | ❌ Rule-based | 🎯 Can improve |
| Subsystem Solvers | ❌ SQL + Scoring | 🎯 Can improve |
| BOM Composer | ❌ Deterministic | 🎯 Can improve |
| Configuration Generator | ❌ Template-based | 🎯 Can improve |
| Cost Optimization | ❌ Heuristics | 🎯 Can improve |

---

## 🎯 LLM Enhancement Opportunities

### 1. **Smarter Template Matching** (HIGH IMPACT)

**Current**: Keyword matching
```python
if "motor" in input and "can" in input:
    return "can_motor_controller"
```

**LLM-Enhanced**:
```python
# LLM analyzes semantic meaning
prompt = """
User wants: "I need to control a BLDC motor over CAN bus"

Available templates:
1. CAN Motor Controller - For motor control via CAN
2. IoT Sensor Node - For sensor data collection
3. Gateway - For protocol bridging

Which template best matches? Consider:
- Primary function
- Communication protocol
- Device type
- Use case similarity

Respond with template ID and confidence.
"""

# LLM Response:
{
  "template_id": "can_motor_controller",
  "confidence": 0.95,
  "reasoning": "Primary function is motor control, CAN is communication method, BLDC is motor type"
}
```

**Benefit**: Better matches for ambiguous inputs

---

### 2. **Intelligent Constraint Optimization** (HIGH IMPACT)

**Current**: Fixed rules
```yaml
rule: "if motor_type == BLDC"
  action: set pwm_timers = 3
```

**LLM-Enhanced**:
```python
# LLM suggests optimal constraints
prompt = """
User wants to control a BLDC motor at 24V, 10A peak current.

Current constraints:
- PWM timers: 3
- ADC channels: 3
- MCU speed: 168 MHz

Are these optimal? Consider:
- BLDC requires 3-phase PWM (6 channels with complementary)
- Current sensing needs 3 ADC channels
- FOC algorithm needs ~100 MHz minimum
- Safety margins

Suggest optimizations.
"""

# LLM Response:
{
  "optimizations": [
    {
      "constraint": "pwm_timers",
      "current": 3,
      "suggested": 1,
      "reasoning": "Need 1 advanced timer with 6 channels (3 complementary pairs), not 3 separate timers"
    },
    {
      "constraint": "min_mhz",
      "current": 168,
      "suggested": 180,
      "reasoning": "FOC at 20kHz PWM needs headroom for other tasks"
    }
  ]
}
```

**Benefit**: More accurate, optimized designs

---

### 3. **Context-Aware Component Selection** (MEDIUM IMPACT)

**Current**: Pure scoring
```python
score = headroom + peripherals + ecosystem
```

**LLM-Enhanced**:
```python
# LLM considers context
prompt = """
Selecting MCU for BLDC motor controller at 24V, 10A.

Top candidates by score:
1. STM32F405RGT6 - $5.50, 168MHz, 1MB Flash
2. STM32F446RET6 - $5.80, 180MHz, 512KB Flash
3. STM32H743VIT6 - $9.20, 480MHz, 2MB Flash

Context:
- User is building prototype (not production)
- Budget sensitive
- Needs USB for debugging
- Wants good documentation

Which should we recommend first? Consider:
- Cost vs performance
- Community support
- Development tools
- Future scalability
"""

# LLM Response:
{
  "recommendation": "STM32F405RGT6",
  "reasoning": "Best balance for prototype: proven platform, extensive community support, affordable, sufficient performance. H743 is overkill for prototype.",
  "alternatives_reasoning": {
    "F446": "Slightly faster but less community support",
    "H743": "Excellent but 70% more expensive, unnecessary for prototype"
  }
}
```

**Benefit**: Better recommendations considering user context

---

### 4. **Intelligent Compatibility Checking** (HIGH IMPACT)

**Current**: Hard-coded rules
```python
if mcu.voltage != transceiver.voltage:
    add_level_shifter()
```

**LLM-Enhanced**:
```python
# LLM analyzes compatibility
prompt = """
BOM components:
- MCU: STM32F405 (3.3V I/O, 5V tolerant)
- CAN Transceiver: SN65HVD230 (3.3V)
- Current Sensor: INA226 (I2C, 2.7-5.5V)
- Power Supply: TPS62160 (3.3V output, 1A)

Check compatibility:
1. Voltage levels
2. Current budget
3. Interface compatibility
4. Thermal considerations
5. PCB layout concerns

Identify issues and suggest fixes.
"""

# LLM Response:
{
  "issues": [
    {
      "severity": "warning",
      "component": "Power Supply",
      "issue": "1A output may be tight",
      "calculation": "MCU: 0.15A + CAN: 0.07A + Sensor: 0.002A + Margin: 0.2A = 0.422A (OK, but only 58% margin)",
      "suggestion": "Consider TPS62162 (1.5A) for better margin"
    }
  ],
  "compatibility": "COMPATIBLE_WITH_WARNINGS"
}
```

**Benefit**: Catches subtle compatibility issues

---

### 5. **Smart Configuration Generation** (MEDIUM IMPACT)

**Current**: Template-based
```python
config = {
    "clock": default_clock_config,
    "pins": default_pin_mapping
}
```

**LLM-Enhanced**:
```python
# LLM generates optimal configuration
prompt = """
Generate STM32F405 configuration for BLDC motor controller.

Requirements:
- 3-phase PWM at 20kHz
- 3 current sensors (ADC)
- CAN communication
- USB for debugging
- Encoder input (quadrature)

Constraints:
- Minimize pin conflicts
- Optimize for PCB routing
- Use DMA where beneficial

Generate:
1. Clock configuration
2. Pin assignments
3. DMA channels
4. Interrupt priorities
"""

# LLM Response:
{
  "clock": {
    "hse_mhz": 8,
    "pll_config": "optimized for 168MHz with USB",
    "apb1_mhz": 42,
    "apb2_mhz": 84,
    "reasoning": "APB1 at 42MHz allows CAN, APB2 at 84MHz for timers"
  },
  "pins": {
    "TIM1_CH1": "PA8 (Phase A PWM)",
    "TIM1_CH1N": "PA7 (Phase A PWM complementary)",
    "reasoning": "TIM1 channels grouped for easier routing"
  },
  "dma": {
    "ADC1": "DMA2_Stream0 (current sensing)",
    "reasoning": "Frees CPU for FOC calculations"
  }
}
```

**Benefit**: Optimal, conflict-free configurations

---

### 6. **Natural Language Explanations** (HIGH IMPACT - UX)

**Current**: Technical jargon
```
"Selected STM32F405RGT6 due to score: 87"
```

**LLM-Enhanced**:
```python
# LLM explains in user's language
prompt = """
Explain why we chose STM32F405RGT6 for BLDC motor controller.

User level: Intermediate (knows basics, not expert)

Technical reasons:
- Has 2 CAN controllers (requirement: 2)
- 168 MHz (sufficient for FOC)
- 1MB Flash (256KB required, 4x headroom)
- Proven platform with good community

Make it understandable and helpful.
"""

# LLM Response:
"We selected the STM32F405RGT6 because:

1. **CAN Communication**: It has 2 built-in CAN controllers, perfect for your motor control network.

2. **Processing Power**: At 168 MHz, it's fast enough to run advanced motor control algorithms (FOC) smoothly at 20kHz PWM frequency.

3. **Memory**: With 1MB of Flash, you have 4x more space than the minimum needed. This gives you room to add features later without changing the MCU.

4. **Community Support**: This is one of the most popular STM32 chips, so you'll find tons of examples, libraries, and help online.

5. **Cost**: At $5.50, it's affordable while being powerful enough for professional motor control.

**Alternative**: If budget is very tight, the STM32F103 ($3.50) could work but with less headroom."
```

**Benefit**: Users understand WHY, not just WHAT

---

## 🎯 Implementation Priority

### Phase 1 (Immediate - High Impact)
1. ✅ **DONE**: LLM-driven dynamic questioning
2. ✅ **DONE**: LLM-enhanced template matching
3. ✅ **DONE**: Natural language explanations

### Phase 2 (Short Term - Medium Impact)
4. ✅ **DONE**: Intelligent constraint optimization
5. 🔄 **TODO**: Context-aware component selection
6. 🔄 **TODO**: Smart compatibility checking

### Phase 3 (Long Term - Nice to Have)
7. 🔄 **TODO**: LLM configuration generation
8. 🔄 **TODO**: Design review and suggestions
9. 🔄 **TODO**: Learning from user feedback

---

## 📊 Summary

### What Each Component Does

| Component | Input | Process | Output |
|-----------|-------|---------|--------|
| **Architecture Compiler** | Template + Answers | Apply rules, build graph | RequirementSpec (constraints) |
| **Subsystem Solvers** | RequirementSpec | Query database, filter, rank | Component recommendations |
| **BOM Composer** | All solver outputs | Check compatibility, add passives | Complete BOM |

### Current LLM Usage

✅ Intent Classification  
✅ Dynamic Questioning  
✅ Template Matching  
✅ Constraint Optimization  
✅ Explanations  
❌ Context-Aware Component Selection (Planned)  
❌ Smart BOM Compatibility Checking (Planned)  
❌ Configuration Generation via LLM (Planned)  
❌ Design Review & Suggestions (Planned)  
❌ Learning from User Feedback (Planned)  

### The Balance

**Keep Deterministic**:
- Hard filtering (must be exact)
- Evidence tracking (must be verifiable)
- Cost calculations (must be accurate)

**Add LLM Intelligence**:
- Understanding user intent
- Optimizing constraints
- Explaining decisions
- Handling edge cases
- Learning from context

**Result**: Best of both worlds - deterministic correctness + intelligent assistance!
