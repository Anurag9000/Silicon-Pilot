# ⚡ HardwareGenius (Production Grade)

**Engineering-Grade AI Hardware Architect & Component Recommender**

HardwareGenius is a **deterministic, parametric hardware-selection engine** that provides evidence-backed recommendations. Unlike generic AI chatbots, it uses a **deterministic constraint solver** over a **PostgreSQL parametric database** with **full provenance**.

Every recommendation is **deterministic**, **constraint-verified**, and **citation-backed** with datasheet references.

![Status](https://img.shields.io/badge/Status-Production_Ready-success)
![Coverage](https://img.shields.io/badge/Evidence-100%25_Grounded-blue)
![Architecture](https://img.shields.io/badge/Architecture-Hybrid_Neurosymbolic-purple)

---

## 🛡️ Anti-Hallucination Architecture

We use a strict 6-layer architecture to ensure **zero hallucination** of hardware specifications.

```mermaid
graph TD
    subgraph "Truth Layer (Deterministic)"
        DB[(PostgreSQL\nParametric DB)]
        Datasheets[Datasheets\n(PDF/HTML)]
        Evidence[Evidence Store\n(Snippets/BBox)]
    end

    subgraph "Logic Layer (Verified)"
        Solver[Deterministic Solver\n(Hard Constraints)]
        Validator[Constraint\nValidator]
        Compiler[Architecture\nCompiler]
    end

    subgraph "Interface Layer (LLM)"
        Intent[User Intent\nParser]
        Optimizer[Intelligent\nOptimizer]
        Explainer[Natural Language\nExplainer]
    end

    Datasheets -->|Ingestion| DB
    Datasheets -->|Extraction| Evidence
    DB --> Solver
    
    Intent --> Compiler
    Compiler -->|Baseline| Optimizer
    Optimizer -->|Optimization| Validator
    Validator -->|Verified Constraints| Solver
    
    Solver -->|Candidates| Explainer
    Evidence -->|Citations| Explainer
    Explainer -->|Verified Response| User([User])

    style DB fill:#e1f5fe,stroke:#01579b
    style Solver fill:#e8f5e9,stroke:#2e7d32
    style Intent fill:#fff3e0,stroke:#ef6c00
    style Validator fill:#fce4ec,stroke:#880e4f
```

[**📖 Read Full Anti-Hallucination Guide**](docs/ANTI_HALLUCINATION.md)

---

## 🚀 Key Features

### 🧠 Intelligent Architecture Synthesis
- **Intent-to-Spec**: Converts "I want to build a drone" into engineering constraints.
- **Smart Optimization**: LLM suggests optimizations (e.g., "Use TIM1 for BLDC FOC") that are validated against hardware reality.
- **Context-Aware**: Adapts recommendations for prototypes vs. mass production.

### ⚙️ Deterministic Selection Engine
- **Zero Hallucination**: No specs are invented. All data is verified from manufacturers.
- **100% Constraint Satisfaction**: Hard requirements are guaranteed to be met.
- **Multi-Subsystem Solving**: simultaneously solves for MCU, Power, Comms, and Sensors.

### 📚 Evidence-Backed RAG
- **Datasheet Provenance**: Direct links to manufacturer PDFs.
- **Snippet Rendering**: Visual proof for every recommended value.
- **Conflict Detection**: Identifies discrepancies between sources.

---

## 📖 Key Documentation

### Core Architecture
| Document | Description |
|----------|-------------|
| [**System Pipeline**](docs/PIPELINE.md) | Visual guide to Architecture Compiler & Solvers. |
| [**Anti-Hallucination**](docs/ANTI_HALLUCINATION.md) | How we prevent AI errors (6-layer architecture). |
| [**System Architecture**](docs/SYSTEM.md) | Technical deep dive into filters & solvers. |
| [**LLM Roadmap**](docs/LLM_ROADMAP.md) | Plan for advanced intelligence features. |

### Guides & Operations
| Document | Description |
|----------|-------------|
| [**Deployment Guide**](docs/DEPLOYMENT.md) | Production setup (Docker/Cloud). |
| [**Run Instructions**](docs/RUNNING.md) | Local development setup. |
| [**Data Ingestion**](docs/DATA_INGESTION.md) | How to collect & ingest datasheets. |
| [**Testing Guide**](docs/TESTING.md) | Unit, Integration, and Golden tests. |
---

## 🏗️ Quick Start

### 1. Requirements
- Docker & Docker Compose
- OpenAI API Key

### 2. Startup
```powershell
# Edit .env and add your OPENAI_API_KEY
docker compose up -d
```

### 3. Access
- **Web UI**: `http://localhost:8001`
- **API Docs**: `http://localhost:8001/docs`

---

## 🧪 Implementation Status

| Component | Status | Description |
|-----------|--------|-------------|
| **Database** | ✅ Done | PostgreSQL with evidence tracking |
| **Ingestion** | ✅ Done | Automated extraction for STM32, TI, NXP |
| **Solver** | ✅ Done | Zero-tolerance hard filter + ranking |
| **AI Layer** | ✅ Done | Intelligent Optimizer + Question Engine |
| **Web UI** | ✅ Done | Production-grade React/FastAPI interface |

---

**Version:** 1.0.0 (Production Release)
**License:** MIT
