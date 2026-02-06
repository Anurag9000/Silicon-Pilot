# ⚡ HardwareGenius
**AI-Powered MCU & Component Selection System**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![Framework: Deterministic AI](https://img.shields.io/badge/Framework-Deterministic_AI-purple.svg)](#)

HardwareGenius is a **deterministic, parametric hardware-selection engine** where an LLM serves as the reasoning/interface layer, while actual MCU/component selection happens through structured, verified spec databases with RAG over datasheets.

**Unlike ChatGPT:** Every recommendation is deterministic, constraint-verified, and citation-backed with datasheet references.

---

## 🎯 The Problem

Traditional hardware selection is:
- ⏰ **Time-consuming:** Hours spent comparing datasheets
- ❌ **Error-prone:** Easy to miss critical specifications
- 🎲 **Unreliable with ChatGPT:** Probabilistic, non-deterministic, hallucinates specs

**HardwareGenius solves this** with engineer-grade, deterministic recommendations.

---

## 🚀 Key Features

### ⚙️ Deterministic Selection Engine
- **Same input → Same output** (unlike ChatGPT)
- **100% constraint satisfaction** for hard requirements
- **Multi-criteria optimization** (cost, power, performance)

### 📊 Parametric Database
- **50+ MCUs** from major manufacturers (STM32, ESP32, nRF, RP2040, SAMD, MSP430)
- **Structured specifications:** Core, RAM, Flash, peripherals, temp range, package, cost
- **Expandable architecture** for easy database updates

### 📚 Datasheet RAG System
- **Citation-backed recommendations** with datasheet page references
- **Table extraction** from PDF datasheets
- **Specification verification** against manufacturer data

### 🤖 AI-Driven Reasoning
- **Natural language interface:** "I need a low-power MCU for IoT"
- **Trade-off analysis:** Cost vs Performance vs Power
- **Iterative refinement:** Add constraints to narrow down options

---

## 🛠️ How It Works

```
User Input (Natural Language)
    ↓
Constraint Parser (LLM-assisted)
    ↓
Parametric Filter (Deterministic)
    ↓
Multi-Criteria Ranking
    ↓
Datasheet RAG (Citation Lookup)
    ↓
Justified Recommendations
```

### Example Interaction

```
You> I need an ARM Cortex-M4 with at least 128KB RAM, 512KB Flash, 
     USB support, and costs under $5

HardwareGenius> Analyzing requirements...
Detected constraints:
  - Core: ARM Cortex-M4
  - RAM: ≥ 128 KB
  - Flash: ≥ 512 KB
  - Peripherals: USB
  - Cost: < $5.00

Filtering database... Found 12 candidates.

Top 3 Recommendations:

1. STM32F405RG (ARM Cortex-M4, 192KB RAM, 1MB Flash, $4.20)
   ✅ All constraints satisfied
   📊 USB 2.0 Full-Speed [Datasheet p.23]
   ⚡ 168 MHz max frequency [Datasheet p.45]
   💰 Cost-effective for performance tier
   
2. STM32F446RE (ARM Cortex-M4, 128KB RAM, 512KB Flash, $4.50)
   ✅ All constraints satisfied
   📊 USB OTG Full-Speed [Datasheet p.28]
   ⚡ 180 MHz max frequency [Datasheet p.52]
   🔧 Rich peripheral set: 4×UART, 4×SPI, 3×I2C
   
3. ESP32-S3 (Xtensa LX7, 512KB RAM, 384KB ROM + 8MB Flash, $2.80)
   ✅ All constraints satisfied
   📊 USB OTG 1.1 [Datasheet p.15]
   📡 Built-in WiFi + Bluetooth [Datasheet p.8]
   💰 Best value with wireless connectivity

Would you like to:
- Compare these side-by-side?
- Add more constraints?
- See detailed specifications?
```

---

## 📖 Quick Start

### 1. Installation
```powershell
git clone https://github.com/Anurag9000/HardwareGenius
cd HardwareGenius
pip install -r requirements.txt
```

### 2. Configuration
```powershell
$env:OPENAI_API_KEY="sk-..."  # Required for AI reasoning
```

### 3. Usage Examples

**Interactive CLI:**
```powershell
python hardware_advisor_cli.py
```

**REST API Server:**
```powershell
python server.py
# API available at http://localhost:8000
```

**Docker:**
```powershell
docker-compose up --build
```

---

## 🏗️ Architecture

### Core Components

1. **Hardware Database Layer** (`hardware_db/`)
   - MCU parametric database
   - Component specifications
   - Manufacturer data models

2. **Filtering Engine** (`filtering/`)
   - Constraint parser (NL → structured constraints)
   - Parametric filter (deterministic selection)
   - Multi-criteria ranking algorithm

3. **Datasheet RAG** (`tools/`)
   - PDF datasheet ingestion
   - Table extraction
   - Citation-backed retrieval

4. **AI Reasoning Layer** (`hardware_advisor.py`)
   - Natural language interface
   - Trade-off analysis
   - Recommendation justification

---

## 🆚 HardwareGenius vs ChatGPT

| Feature | HardwareGenius | ChatGPT |
|---------|---------------|---------|
| **Determinism** | ✅ Same input → Same output | ❌ Probabilistic |
| **Constraint Verification** | ✅ 100% satisfaction guaranteed | ❌ May miss requirements |
| **Citations** | ✅ Every claim has datasheet reference | ❌ No source verification |
| **Spec Accuracy** | ✅ Verified against manufacturer data | ❌ May hallucinate specs |
| **Engineer-Grade** | ✅ Production-ready recommendations | ❌ Requires manual verification |
| **Database** | ✅ Structured, verified specs | ❌ Unstructured training data |

---

## 📂 Project Structure

```
HardwareGenius/
├── hardware_db/          # MCU/component database
│   ├── models.py         # Data models
│   ├── mcu_database.py   # MCU specifications
│   └── component_database.py
├── filtering/            # Deterministic filtering engine
│   ├── constraint_parser.py
│   ├── parametric_filter.py
│   └── ranking.py
├── tools/                # Datasheet RAG & utilities
│   ├── datasheet_rag.py
│   ├── datasheet_ingestion.py
│   └── verification.py
├── hardware_advisor.py   # Main AI orchestration
├── hardware_advisor_cli.py  # Interactive CLI
├── server.py             # FastAPI REST API
└── tests/                # Comprehensive test suite
```

---

## 🎓 Use Cases

### 1. Battery-Powered IoT Sensor
```
Requirements: Ultra-low power, I2C, small package
Recommendation: STM32L476 (0.29 µA standby)
```

### 2. High-Performance Motor Controller
```
Requirements: Fast ADC, PWM, 200+ MHz, FPU
Recommendation: STM32H743 (480 MHz, dual-core)
```

### 3. Cost-Optimized Consumer Device
```
Requirements: Basic GPIO, UART, < $1
Recommendation: STM32F030 ($0.85, ARM Cortex-M0)
```

### 4. Industrial Temperature Range
```
Requirements: -40°C to +125°C, CAN bus, robust
Recommendation: STM32F407 (industrial grade)
```

---

## 🧪 Testing & Validation

### Automated Tests
- ✅ Constraint parsing accuracy
- ✅ Filtering engine determinism
- ✅ Citation verification
- ✅ End-to-end recommendation flow

### Manual Validation
- ✅ Comparison with manual datasheet search
- ✅ Verification against ChatGPT (determinism test)
- ✅ Real-world engineering scenarios

---

## 🤝 Contributing

We welcome contributions! Areas for expansion:
- Additional MCU families (AVR, PIC, ARM Cortex-A)
- More component types (sensors, power management, connectors)
- Enhanced filtering algorithms
- Datasheet parsing improvements

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

Built for the **Embedded System Design (ESD)** course project.

**Key Differentiator:** Deterministic, constraint-verified hardware selection vs probabilistic ChatGPT recommendations.

---

*Created by [Anurag9000](https://github.com/Anurag9000)*

**Status:** 🚧 Active Development | **Version:** 0.1.0-alpha
