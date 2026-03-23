# Silicon-Pilot (HardwareGenius)

**Engineering-Grade MCU Selection Engine with Explainable AI**

![System Architecture Diagram](architecture_diagram.png)

Silicon-Pilot ingests real STM32 datasheet PDFs and provides deep parametric analysis, architectural validation, exhaustive parameter traceability, and cross-component compatibility checks.

---

## ✅ Implemented Features

| Feature | Endpoint / Module |
|---|---|
| **Natural Language Requirements Parsing** | `POST /spec/from_text` |
| **ML-Ranked MCU Candidate Recommendations** | `POST /recommend` |
| **AI Peer Review (Architect's Notes)** — senior engineer sanity check with pass/warn/fail verdict | `POST /api/peer-review` |
| **Smart BOM Compatibility Checking** — voltage, power, interface cross-validation | `POST /api/bom/check` |
| **Head-to-Head AI Debate** — two candidates argued by AI advocates | `POST /api/debate` |
| **Comparison Matrix** — structured parameter table across candidates | `POST /api/compare` |
| **Thermal Dissipation Analysis** — θJA checks, derating, package thermal constraints | Built into peer-review |
| **Deep PDF Parameter Extraction** — 587 params extracted from STM32H743 datasheet alone | `ingestion/deep_datasheet_extractor.py` |
| **Exhaustive Parameter Verification UI** — every param, by section, with PDF page provenance | `POST /api/exhaustive-review` |

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
| [workflow.md](workflow.md) | Detailed ingestion and runtime workflow |
| [database/schema.sql](database/schema.sql) | Full PostgreSQL schema with all tables |
