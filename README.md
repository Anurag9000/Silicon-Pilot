# Silicon-Pilot (HardwareGenius)

**Engineering-Grade MCU Selection Engine with Explainable AI**

Silicon-Pilot ingests real STM32 datasheet PDFs and provides deep parametric analysis, architectural validation, exhaustive parameter traceability, and cross-component compatibility checks.

---

## ✅ Implemented Dream Specs

| # | Dream Spec | Status | Endpoint / Module |
|---|---|---|---|
| DS1 | **Context-Aware Component Selection** — re-rank based on user context (budget, volume, ecosystem) | ❌ **Not implemented** | — |
| DS2 | **Smart BOM Compatibility Checking** — cross-validates entire board for voltage, power, interface conflicts | ✅ Done | `POST /api/bom/check` → `solver/bom_checker.py` |
| DS3 | **LLM-Driven Config Generation (CubeMX / Firmware)** — generate `.ioc` / C scaffolding | ⚠️ **Stub only** — static rules, no LLM, no `.ioc` output | `architecture/config_generator.py` |
| DS4 | **AI Peer Review (Architect's Notes)** — senior engineer sanity-check with pass/warn/fail verdict | ✅ Done | `POST /api/peer-review` → `llm/rigorous_explainer.py` |

### Additional Features (beyond original Dream Specs)
| Feature | Status | Details |
|---|---|---|
| **Thermal Dissipation Analysis** | ✅ Done | θJA per package, power dissipation, derating curves in peer-review |
| **Exhaustive Datasheet Parameter Verification** | ✅ Done | 587 parameters extracted from STM32H743 PDF; all shown in UI with section + page provenance |
| **Deep PDF Extraction Pipeline** | ✅ Done | `ingestion/deep_datasheet_extractor.py` extracts DC, AC, thermal, current, clock, GPIO, features |
| **Explainable AI UI (parameter-by-parameter)** | ✅ Done | Full modal with section headers, pg. badges, fit score legend |

---

## 🚀 Quick Start

```bash
# Start with mock SQLite (no Postgres needed)
LOCAL_LLM=true DEMO_MODE=true python server.py

# Access UI at:
http://localhost:8000
```

**To extract all datasheet parameters into DB:**
```bash
source .venv/bin/activate
python scripts/populate_datasheet_params.py
```

**To run with real Postgres:**
```bash
export DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius'
python scripts/run_pipeline.py
python server.py
```

---

## 📖 Documentation

| Doc | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, component breakdown, data flow |
| [TODO_DREAM_SPECS.md](TODO_DREAM_SPECS.md) | Exact gaps for remaining dream specs |
| [workflow.md](workflow.md) | Detailed ingestion and runtime workflow |
| [database/schema.sql](database/schema.sql) | Full PostgreSQL schema with all tables |

---

## 🔑 Key API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /spec/from_text` | Parse natural language requirements |
| `POST /recommend` | Get ranked MCU candidates |
| `POST /api/peer-review` | AI Architect's Review (DS4) |
| `POST /api/exhaustive-review` | Parameter-by-parameter verification with PDF provenance |
| `POST /api/bom/check` | BOM cross-compatibility check (DS2) |
| `POST /api/debate` | Head-to-head AI debate between two candidates |
| `POST /api/compare` | Structured comparison matrix |
