# Silicon-Pilot (Silicon-Pilot)

**Engineering-Grade MCU Selection Engine with Explainable AI**

![System Architecture Diagram](architecture_diagram.png)

Silicon-Pilot ingests real STM32 datasheet PDFs and provides deep parametric analysis, architectural validation, exhaustive parameter traceability, and cross-component compatibility checks.

---

##  Implemented Features

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

##  Quick Start

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
export DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot'
python scripts/run_pipeline.py
python server.py
```

---

##  Documentation

| Doc | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, component breakdown, data flow |
| [workflow.md](workflow.md) | Detailed ingestion and runtime workflow |
| [database/schema.sql](database/schema.sql) | Full PostgreSQL schema with all tables |

## Advanced Engineering Features

### Advanced Engineering Features
- **Drop-In Replacement Engine**: Input an EOL part, and the system ranks pin-to-pin and software-compatible alternatives based on the level of schematic rework needed (Drop-In, Minor, Moderate, Major).
- **Advanced Power Profiler**: Define custom duty cycles (Run, Sleep, Stop) and active peripherals. The tool computes real-world average current draw and estimated battery life using Peukert-corrected chemistry derating from datasheet seed data.
- **PCB Manufacturing Cost Analyzer**: Evaluates the mechanical complexity of MCU packages (LQFP, BGA, WLCSP, etc.), predicts required PCB layers, identifies HDI (High Density Interconnect) requirements, and provides a raw cost multiplier.
- **Component Ecosystem RAG**: Recommends complete, matched chipsets (CAN transceivers, motor drivers, LDOs, IMUs) that share logic-level compatibility and interface constraints with the selected MCU.


##  Live End-to-End Demo

Watch Silicon-Pilot autonomously analyze requirements, compare hardware, solve pin muxing, evaluate power/package constraints, and build a full ecosystem BOM:

![Silicon-Pilot Live Demo](docs/silicon_pilot_live_demo.webp)


##  Changing the LLM Model
Silicon-Pilot uses Ollama by default for fully local, private AI inference. If you want to change the underlying model (e.g., from `qwen2.5:1.5b` to `llama3.2` or switch to OpenAI):

1. Open the file: `core/llm_config.py`
2. At the very top, locate the configuration variables:
   ```python
   LLM_PROVIDER = "ollama"       # Options: "ollama", "openai", "gemini", "anthropic"
   LLM_MODEL = "qwen2.5:1.5b"    # The default model name
   ```
3. **To use a different local model**, run `ollama pull <model_name>` in your terminal, then update the `LLM_MODEL` variable.
4. **To use a cloud provider**, change `LLM_PROVIDER = "openai"`, set `LLM_MODEL = "gpt-4o"`, and ensure your `.env` file has the `OPENAI_API_KEY`.
