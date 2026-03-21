# HardwareGenius

**Engineering-Grade Component Selection Engine**

HardwareGenius is a system designed to ingest raw datasheet PDFs and serve deep parametric data for electronic components. It moves beyond simple "filters" to provide architectural validation, intelligent recommendations, and cross-compatibility checks.

## ✨ Implemented Dream Specs
We have recently implemented major architectural "Dream Specs" to elevate this from a basic search engine to a peer-review tool:
1. **AI Peer Review (Architect's Notes)**: `POST /api/peer-review` — Triggers an LLM to review the top component candidate just like a senior hardware engineer, warning about missing constraints, overkill selections, and providing a color-coded "pass/fail/warn" verdict.
2. **Smart BOM Compatibility Checking**: `POST /api/bom/check` — A rules-based engine that cross-references all components added to a BOM cart. It checks voltage level overlaps (e.g., 3.3V vs 1.8V), power supply adequacy (LDO output vs MCU drain), interface scaling, and CAN transceiver pairings.

## 🚀 Quick Start

To set up the database, seed initial data, and run the ingestion pipeline:

```bash
# Windows
$env:DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius'; python scripts/run_pipeline.py

# Linux/Mac
export DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius'
python scripts/run_pipeline.py
```

## 📖 Documentation

*   **[Features & Capabilities](features.md)**: Exhaustive list of all supported components and system features.
*   **[System Workflow](system_workflow.md)**: Detailed step-by-step explanation of ingestion and runtime flows.
*   **[Architecture & Design](architecture.md)**: High-level system design and component breakdown.
*   **[Remaining Tasks](remaining.md)**: Roadmap of pending features (Context-Aware Ranking, CubeMX generation).

## 💻 Usage

Start the API Server (Supports both Mock SQLite and Production PostgreSQL via UI hot-swapping):
```bash
python server.py
```
Access the UI at `http://localhost:8000`.
