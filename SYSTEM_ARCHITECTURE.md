# HardwareGenius System Architecture

## Overview

HardwareGenius is a **deterministic AI-powered hardware selection system** that combines structured parametric databases with LLM reasoning to provide engineer-grade MCU and component recommendations.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        User Interface                        │
│  ┌──────────────────┐              ┌───────────────────┐   │
│  │  CLI Interface   │              │   REST API        │   │
│  │  (Interactive)   │              │   (FastAPI)       │   │
│  └────────┬─────────┘              └─────────┬─────────┘   │
└───────────┼────────────────────────────────────┼────────────┘
            │                                    │
            └────────────────┬───────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                   AI Reasoning Layer                         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         HardwareAdvisor (Main Orchestrator)          │  │
│  │  - Natural Language Understanding                     │  │
│  │  - Tool Selection & Execution                        │  │
│  │  - Response Generation                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         │                   │                   │           │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐   │
│  │  Constraint  │    │  Trade-off  │    │ Justification│   │
│  │   Parser     │    │  Analyzer   │    │   Generator  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│              Deterministic Filtering Engine                  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Parametric Filter (Core Logic)               │  │
│  │  1. Hard Constraint Filtering                        │  │
│  │  2. Soft Constraint Scoring                          │  │
│  │  3. Multi-Criteria Ranking                           │  │
│  └──────────────────────────────────────────────────────┘  │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         │                   │                   │           │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐   │
│  │   Cost      │    │   Power     │    │ Performance │   │
│  │  Optimizer  │    │  Optimizer  │    │  Optimizer  │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                   Data Layer                                 │
│                                                              │
│  ┌──────────────────┐              ┌───────────────────┐   │
│  │  Hardware DB     │              │  Datasheet RAG    │   │
│  │  (Parametric)    │              │  (ChromaDB)       │   │
│  │                  │              │                   │   │
│  │  - MCU Specs     │              │  - PDF Ingestion  │   │
│  │  - Components    │              │  - Table Extract  │   │
│  │  - Manufacturers │              │  - Citation Lookup│   │
│  └──────────────────┘              └───────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. User Interface Layer

#### CLI Interface (`hardware_advisor_cli.py`)
- Interactive terminal-based interface
- Real-time constraint refinement
- Formatted output with tables and citations

#### REST API (`server.py`)
- FastAPI-based HTTP endpoints
- JSON request/response format
- Asynchronous processing for large queries

**Key Endpoints:**
```python
POST /api/recommend        # Get MCU recommendations
POST /api/compare          # Compare multiple MCUs
GET  /api/datasheet/{part} # Retrieve datasheet info
POST /api/refine           # Refine previous recommendations
```

---

### 2. AI Reasoning Layer

#### HardwareAdvisor (`hardware_advisor.py`)
**Purpose:** Main orchestration and LLM interaction

**System Prompt:**
```
You are an expert hardware selection advisor. Your role is to:
1. Parse user requirements into structured constraints
2. Filter MCU/component databases deterministically
3. Rank candidates by multi-criteria optimization
4. Justify every recommendation with datasheet citations
5. Explain trade-offs clearly

CRITICAL: Every recommendation MUST be:
- Deterministic (same input → same output)
- Constraint-verified (all MUST-haves satisfied)
- Citation-backed (datasheet references for all claims)
```

**Tool Definitions:**
```python
TOOLS_SCHEMA = [
    PARSE_REQUIREMENTS_TOOL,      # NL → structured constraints
    FILTER_MCU_DATABASE_TOOL,     # Deterministic parametric filtering
    RANK_CANDIDATES_TOOL,         # Multi-criteria ranking
    DATASHEET_LOOKUP_TOOL,        # RAG over datasheets
    COMPARE_COMPONENTS_TOOL,      # Side-by-side comparison
    JUSTIFY_RECOMMENDATION_TOOL,  # Citation-backed explanation
    TRADE_OFF_ANALYSIS_TOOL       # Cost vs Performance vs Power
]
```

#### Constraint Parser (`filtering/constraint_parser.py`)
**Purpose:** Convert natural language to structured constraints

**Input:**
```
"I need an ARM Cortex-M4 with at least 128KB RAM, 512KB Flash, 
 USB support, and costs under $5"
```

**Output:**
```python
{
    "hard_constraints": {
        "core_architecture": "ARM Cortex-M4",
        "ram_kb": {"min": 128},
        "flash_kb": {"min": 512},
        "peripherals": ["USB"],
        "cost_usd": {"max": 5.0}
    },
    "soft_constraints": {},
    "optimization_goal": "cost"
}
```

---

### 3. Deterministic Filtering Engine

#### Parametric Filter (`filtering/parametric_filter.py`)
**Purpose:** Core deterministic selection logic

**Algorithm:**
```python
def filter_mcus(constraints: Dict, database: List[MCUSpec]) -> List[MCUSpec]:
    # Step 1: Hard constraint filtering (MUST satisfy)
    candidates = []
    for mcu in database:
        if satisfies_all_hard_constraints(mcu, constraints):
            candidates.append(mcu)
    
    # Step 2: Soft constraint scoring (NICE to have)
    scored = []
    for mcu in candidates:
        score = calculate_soft_score(mcu, constraints)
        scored.append((mcu, score))
    
    # Step 3: Multi-criteria ranking
    ranked = multi_criteria_rank(scored, constraints["optimization_goal"])
    
    return ranked[:10]  # Top 10 candidates
```

**Determinism Guarantee:**
- No randomness in filtering
- Consistent scoring functions
- Stable sorting (tie-breaking by part number)

#### Multi-Criteria Ranking (`filtering/ranking.py`)
**Purpose:** Optimize across multiple objectives

**Criteria:**
- **Cost:** Price per unit (lower is better)
- **Power:** Active + standby current (lower is better)
- **Performance:** Clock speed, DMIPS (higher is better)
- **Peripherals:** Number of matched peripherals (higher is better)
- **Availability:** Stock status, lead time (better is better)

**Ranking Algorithm:**
```python
def multi_criteria_rank(candidates, goal="balanced"):
    weights = {
        "cost": {"cost": 0.7, "power": 0.1, "performance": 0.2},
        "power": {"cost": 0.2, "power": 0.6, "performance": 0.2},
        "performance": {"cost": 0.1, "power": 0.1, "performance": 0.8},
        "balanced": {"cost": 0.33, "power": 0.33, "performance": 0.34}
    }
    
    w = weights[goal]
    
    for mcu, base_score in candidates:
        final_score = (
            w["cost"] * normalize_cost(mcu.cost_usd) +
            w["power"] * normalize_power(mcu.power_consumption) +
            w["performance"] * normalize_performance(mcu.clock_mhz)
        )
        mcu.final_score = final_score
    
    return sorted(candidates, key=lambda x: x[1].final_score, reverse=True)
```

---

### 4. Data Layer

#### Hardware Database (`hardware_db/`)

**MCU Data Model:**
```python
@dataclass
class MCUSpec:
    part_number: str
    manufacturer: str
    core_architecture: str  # ARM Cortex-M0/M3/M4/M7, RISC-V, etc.
    clock_mhz: int
    ram_kb: int
    flash_kb: int
    peripherals: List[str]  # UART, SPI, I2C, ADC, USB, CAN, etc.
    temp_range: Tuple[int, int]  # (min, max) in °C
    package: str  # QFN, LQFP, BGA, etc.
    voltage_range: Tuple[float, float]  # (min, max) in V
    cost_usd: float
    power_consumption: Dict[str, float]  # active_ma, standby_ua
    datasheet_url: str
    stock_status: str  # in_stock, limited, obsolete
```

**Initial Database Coverage:**
- **STM32 Family:** F0, F1, F3, F4, F7, H7, L0, L4, L5, G0, G4
- **ESP32 Family:** ESP32, ESP32-S2, ESP32-S3, ESP32-C3, ESP32-C6
- **Nordic nRF:** nRF52832, nRF52840, nRF5340
- **Raspberry Pi:** RP2040, RP2350
- **Microchip SAMD:** SAMD21, SAMD51
- **TI MSP430:** MSP430FR5xxx, MSP430FR6xxx

**Total:** 50+ MCUs in initial database

#### Datasheet RAG (`tools/datasheet_rag.py`)

**Purpose:** Citation-backed specification lookup

**Features:**
- PDF datasheet ingestion with table extraction
- Hierarchical chunking (parent/child)
- Semantic search over specifications
- Citation with page number references

**Example Query:**
```python
query = "What is the standby current of STM32L476?"
result = datasheet_rag.query(query, part_number="STM32L476")

# Output:
{
    "answer": "0.29 µA in Standby mode with RTC",
    "citation": "STM32L476 Datasheet, p.45, Table 23",
    "confidence": 0.95
}
```

---

## Data Flow

### Recommendation Flow

```
1. User Input
   "I need a low-power MCU for battery-powered IoT"
   
2. Constraint Parsing (LLM-assisted)
   {
       "hard_constraints": {"power_consumption": {"standby_ua": {"max": 5}}},
       "soft_constraints": {"peripherals": ["I2C", "SPI"]},
       "optimization_goal": "power"
   }
   
3. Parametric Filtering (Deterministic)
   Database: 50 MCUs → Filter → 8 candidates
   
4. Multi-Criteria Ranking
   Rank by: power (60%), cost (20%), performance (20%)
   
5. Datasheet RAG (Citation Lookup)
   For each candidate, retrieve:
   - Standby current specification
   - Power modes description
   - Peripheral details
   
6. Response Generation (LLM)
   Format recommendations with:
   - Ranked list
   - Justifications
   - Datasheet citations
   - Trade-off analysis
```

---

## Determinism Guarantees

### Sources of Determinism

1. **Parametric Filtering:** Pure function, no randomness
2. **Ranking Algorithm:** Deterministic scoring, stable sort
3. **Database:** Static specs, version-controlled
4. **LLM Usage:** Only for parsing and formatting, NOT for selection

### Non-Deterministic Components (Controlled)

1. **Constraint Parsing:** LLM may parse differently, but constraints are validated
2. **Response Formatting:** LLM may rephrase, but recommendations are fixed

### Verification

```python
# Test determinism
result1 = hardware_advisor.recommend("ARM Cortex-M4, 128KB RAM, USB, <$5")
result2 = hardware_advisor.recommend("ARM Cortex-M4, 128KB RAM, USB, <$5")

assert result1.recommendations == result2.recommendations  # MUST be identical
```

---

## Performance Characteristics

### Latency
- **Constraint Parsing:** ~500ms (LLM call)
- **Parametric Filtering:** ~10ms (in-memory)
- **Datasheet RAG:** ~200ms (vector search)
- **Response Generation:** ~1s (LLM call)
- **Total:** ~2s for typical query

### Scalability
- **Database Size:** O(n) filtering, optimized with indexing
- **Concurrent Users:** FastAPI async support
- **Datasheet RAG:** ChromaDB scales to millions of chunks

---

## Future Enhancements

1. **Expanded Database:**
   - More MCU families (AVR, PIC, ARM Cortex-A)
   - Additional components (sensors, power ICs, connectors)
   - Real-time pricing integration

2. **Advanced Filtering:**
   - Pareto frontier optimization
   - Sensitivity analysis
   - What-if scenarios

3. **Enhanced RAG:**
   - Automatic datasheet updates
   - Image/diagram extraction
   - Cross-reference validation

4. **User Features:**
   - Saved configurations
   - Comparison history
   - Export to BOM (Bill of Materials)

---

## Technology Stack

- **Language:** Python 3.10+
- **LLM:** OpenAI GPT-4o (reasoning layer only)
- **Vector DB:** ChromaDB (datasheet RAG)
- **Web Framework:** FastAPI (REST API)
- **Database:** JSON/SQLite (parametric specs)
- **PDF Processing:** PyMuPDF (datasheet ingestion)
- **Deployment:** Docker + Docker Compose

---

**Status:** 🚧 Active Development | **Version:** 0.1.0-alpha
