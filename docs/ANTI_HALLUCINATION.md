# Anti-Hallucination Architecture

**Critical Question**: How do we ensure everything is grounded in real data and nothing is hallucinated?

---

##  The Core Principle: LLM ≠ Source of Truth

### What LLMs Do (Interface Layer)
 Parse user intent  
 Ask clarifying questions  
 Optimize constraints (suggestions only)  
 Explain decisions in natural language  
 Match templates semantically  

### What LLMs NEVER Do (Truth Layer)
 Generate component specifications  
 Invent part numbers  
 Make up datasheet values  
 Create constraints without validation  
 Recommend components not in database  

---

##  The Multi-Layer Anti-Hallucination System

### Layer 1: Database is the ONLY Source of Truth

**All component data comes from PostgreSQL database**:

```python
#  CORRECT: Query database
candidates = database.query("""
    SELECT * FROM mcu_specs
    WHERE flash_kb >= 256
      AND can_count >= 2
""")

#  NEVER: Ask LLM for specs
# "What MCUs have 256KB Flash and 2 CAN?"  # WRONG!
```

**Database is populated from**:
- Manufacturer datasheets (PDF extraction)
- Official product pages (HTML parsing)
- Verified distributor data (cross-checked)

**Every field has evidence**:
```json
{
  "mpn": "STM32F405RGT6",
  "flash_kb": 1024,
  "evidence": {
    "source": "https://st.com/resource/en/datasheet/stm32f405rg.pdf",
    "page": 12,
    "snippet": "1 Mbyte of Flash memory",
    "hash": "abc123...",
    "extracted_at": "2026-01-15T10:30:00Z"
  }
}
```

---

### Layer 2: LLM Optimization is VALIDATED

**When LLM suggests constraint optimization**:

```python
# LLM suggests
optimization = {
    "field": "pwm_timers",
    "original": 3,
    "optimized": 1,
    "reasoning": "BLDC FOC needs 1 advanced timer with 6 channels"
}

#  VALIDATION STEP 1: Check against MCU capabilities
validator = ConstraintValidator()
is_valid, issues = validator.validate_constraints({
    "peripherals_min": {"pwm_timers": 1}
})

#  VALIDATION STEP 2: Check against database
mcus_with_1_advanced_timer = database.query("""
    SELECT COUNT(*) FROM mcu_specs
    WHERE advanced_timers >= 1
""")

if mcus_with_1_advanced_timer == 0:
    # Reject optimization - no MCUs match
    reject_optimization()

#  VALIDATION STEP 3: Expert review (optional)
if optimization.confidence < 0.8:
    flag_for_human_review()
```

**Result**: LLM can only suggest optimizations that:
1. Are physically possible
2. Have components in database
3. Pass validation rules

---

### Layer 3: Evidence Requirement for ALL Recommendations

**Every recommended component MUST have evidence**:

```python
class ComponentRecommendation:
    mpn: str
    specs: Dict[str, Any]
    evidence: List[Evidence]  # REQUIRED!
    
    def validate(self):
        # Check every spec has evidence
        for field, value in self.specs.items():
            if not self.has_evidence_for(field):
                raise ValueError(f"No evidence for {field}")
```

**If evidence is missing → Component is NOT recommended**:

```python
#  CORRECT: Component with evidence
{
  "mpn": "STM32F405RGT6",
  "flash_kb": 1024,
  "evidence": [...]  # Has evidence
}
# → Recommended ✓

#  REJECTED: Component without evidence
{
  "mpn": "STM32F999XXX",  # Doesn't exist
  "flash_kb": 9999,
  "evidence": []  # No evidence
}
# → NOT recommended ✗
```

---

### Layer 4: Deterministic Solver (Zero LLM Involvement)

**Component selection is 100% deterministic**:

```python
# Step 1: Hard Filter (SQL query, no LLM)
candidates = database.query("""
    SELECT * FROM mcu_specs
    WHERE core = 'cortex-m4'
      AND flash_kb >= 256
      AND sram_kb >= 64
      AND can_count >= 2
      AND status = 'active'
""")

# Step 2: Rank (mathematical formula, no LLM)
for mcu in candidates:
    score = 0
    score += (mcu.flash_kb - 256) / 256 * 20  # Headroom
    score += mcu.ecosystem_score  # Curated score
    score += availability_score(mcu)  # From distributor API
    mcu.total_score = score

# Step 3: Sort (deterministic)
top_10 = sorted(candidates, key=lambda x: x.total_score, reverse=True)[:10]

# NO LLM INVOLVED IN THIS PROCESS!
```

---

### Layer 5: Cross-Validation Against Multiple Sources

**Data ingestion validates across sources**:

```python
# Source 1: Manufacturer datasheet
mfg_data = {
    "flash_kb": 1024,
    "source": "ST datasheet"
}

# Source 2: Distributor (Digi-Key)
dist_data = {
    "flash_kb": 1024,
    "source": "Digi-Key"
}

#  MATCH: Both agree → High confidence
if mfg_data["flash_kb"] == dist_data["flash_kb"]:
    confidence = 0.95
    publish_to_database()

#  CONFLICT: Sources disagree → Flag for review
else:
    create_conflict_record()
    flag_for_human_review()
    # DO NOT publish until resolved
```

---

### Layer 6: Human-in-the-Loop for Low Confidence

**Review queue for uncertain data**:

```python
if extraction_confidence < 0.85:
    add_to_review_queue({
        "mpn": "STM32F405RGT6",
        "field": "flash_kb",
        "extracted_value": "1024",
        "confidence": 0.75,
        "snippet_image": "datasheet_page12_snippet.png"
    })
    
    # Human reviews and approves/rejects
    # Only approved data goes to production database
```

---

##  Specific Anti-Hallucination Safeguards

### Safeguard #1: LLM Constraint Optimization

**What LLM does**:
```
"BLDC FOC needs 1 advanced timer with 6 channels, not 3 separate timers"
```

**What happens next**:
1.  Validate: Do STM32 MCUs have "advanced timers"? → YES
2.  Validate: Can 1 timer provide 6 PWM channels? → YES (TIM1)
3.  Validate: Will this work for BLDC? → YES (industry standard)
4.  Check database: Are there MCUs with this config? → YES (47 MCUs)
5.  Apply optimization

**If ANY validation fails → Reject optimization, use baseline**

---

### Safeguard #2: Context-Aware Component Selection

**What LLM does**:
```
"For prototype phase, recommend F405 over H743 due to better 
community support and lower cost"
```

**What happens next**:
1.  Check: Is F405 in database? → YES
2.  Check: Does F405 meet requirements? → YES (already passed hard filter)
3.  Check: Is H743 in database? → YES
4.  Check: Are prices real? → YES (from database, not LLM)
5.  Re-rank based on context

**LLM only re-orders existing valid candidates, never invents new ones**

---

### Safeguard #3: Smart Compatibility Checking

**What LLM does**:
```
"Power supply 1A output may be tight. MCU: 150mA + CAN: 70mA + 
Sensor: 2mA = 222mA. With 20% margin = 266mA. Recommend 1.5A."
```

**What happens next**:
1.  Validate calculations: 150+70+2 = 222? → YES
2.  Validate margin: 222 * 1.2 = 266? → YES
3.  Check current specs: Are these from database? → YES
4.  Check 1.5A supply exists: Query database → YES (TPS62162)
5.  Show suggestion with evidence

**All numbers come from database, LLM only does arithmetic**

---

### Safeguard #4: Configuration Generation

**What LLM does**:
```
"Configure PLL: HSE=8MHz, PLL_N=336, PLL_P=2 → 168MHz"
```

**What happens next**:
1.  Validate math: 8 * 336 / 2 = 1344? → NO, should be 168
2.  Correct formula: 8 * (336/8) / 2 = 168? → YES
3.  Check against MCU limits: Max PLL_N = 432? → YES
4.  Check against datasheet: Valid config? → YES
5.  Generate .ioc file

**Configuration is validated against MCU reference manual**

---

##  Evidence Tracking Example

**Complete evidence chain for one recommendation**:

```json
{
  "recommendation": {
    "mpn": "STM32F405RGT6",
    "price": 5.50,
    "score": 87.3,
    "rank": 1
  },
  "evidence": [
    {
      "field": "flash_kb",
      "value": 1024,
      "source": "https://st.com/resource/en/datasheet/stm32f405rg.pdf",
      "page": 12,
      "snippet": "1 Mbyte of Flash memory",
      "confidence": 0.98,
      "verified_by": "human_reviewer_123",
      "verified_at": "2026-01-15T10:30:00Z"
    },
    {
      "field": "can_count",
      "value": 2,
      "source": "https://st.com/resource/en/datasheet/stm32f405rg.pdf",
      "page": 15,
      "snippet": "2× CAN 2.0B interfaces",
      "confidence": 0.99,
      "verified_by": "human_reviewer_123",
      "verified_at": "2026-01-15T10:30:00Z"
    },
    {
      "field": "price_usd",
      "value": 5.50,
      "source": "https://www.digikey.com/product-detail/...",
      "retrieved_at": "2026-02-09T12:00:00Z",
      "quantity": 1,
      "note": "Price is volatile, updated daily"
    }
  ],
  "llm_involvement": {
    "constraint_optimization": {
      "applied": true,
      "optimizations": [
        {
          "field": "pwm_timers",
          "original": 3,
          "optimized": 1,
          "validated": true,
          "validation_method": "database_query"
        }
      ]
    },
    "explanation": "Selected for balance of performance, cost, and community support",
    "note": "LLM only provided explanation and optimization suggestions, not specs"
  }
}
```

---

##  Summary: What's Grounded vs What's LLM

### 100% Grounded (Database/Evidence)
 Component specifications (Flash, RAM, peripherals)  
 Part numbers (MPNs)  
 Prices (from distributors, updated regularly)  
 Availability (from distributors)  
 Datasheet excerpts  
 Hard constraint filtering  
 Ranking scores  

### LLM-Assisted (But Validated)
 Constraint optimization suggestions → Validated against database  
 Context-aware re-ranking → Only reorders valid candidates  
 Compatibility analysis → Uses database specs, LLM does arithmetic  
 Configuration generation → Validated against reference manual  

### Pure LLM (Interface Only)
 Natural language explanations  
 Question phrasing  
 Reasoning text  
 User intent parsing  

---

##  The Guarantee

**We guarantee**:

1. **Every recommended component exists in our database**
2. **Every spec has evidence from manufacturer sources**
3. **LLM suggestions are validated before use**
4. **Hard constraints are enforced deterministically**
5. **Prices come from real distributor APIs**
6. **Configurations are validated against datasheets**

**We NEVER**:
1.  Let LLM invent part numbers
2.  Let LLM generate specifications
3.  Trust LLM for numerical values
4.  Recommend components not in database
5.  Use LLM output without validation

---

##  How to Verify (For Users)

**Every recommendation includes**:
-  Evidence links (click to see datasheet)
-  Confidence scores (how certain we are)
-  Source attribution (where data came from)
-  Validation status (passed all checks)

**Example in UI**:
```
Recommended: STM32F405RGT6 ($5.50)

Specifications:
  Flash: 1024 KB [ Evidence: ST Datasheet p.12]
  CAN: 2 controllers [ Evidence: ST Datasheet p.15]
  
Optimization Applied:
  PWM Timers: 3 → 1 (advanced timer)
  Reasoning: "BLDC FOC needs 1 advanced timer..."
  Validated:  YES (47 MCUs in database match)
  
Price: $5.50 [ Digi-Key, updated 2 hours ago]
```

---

**Bottom Line**: LLMs make the system smarter and more user-friendly, but they NEVER generate the truth. Truth comes from datasheets → database → deterministic solver → you.
