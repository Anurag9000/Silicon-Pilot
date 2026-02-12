
# HardwareGenius

**Engineering-Grade Component Selection Engine**

HardwareGenius is a system designed to ingest raw datasheet PDFs and serve deep parametric data for electronic components. It moves beyond simple "filters" to provide architectural validation and intelligent recommendations.

## 🚀 Quick Start (The "One Command")

To set up the database, seed initial data, and run the ingestion pipeline:

```bash
# Windows
$env:DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius'; python scripts/run_pipeline.py

# Linux/Mac
export DATABASE_URL='postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius'
python scripts/run_pipeline.py
```

This script will:
1.  **Reset Database**: Drop and recreate all tables (`schema.sql`).
2.  **Seed Data**: Populate 1,000+ STM32 parts and LDO regulators from known families.
3.  **Download Datasheets**: Fetch PDFs from ST.com (cached in `datasheets/`).
4.  **Extract features**: Parse Pin Mux, Power profiles, and Errata from the PDFs.

## 📖 Documentation

*   **[Features & Capabilities](features.md)**: Exhaustive list of all supported components and system features.
*   **[System Workflow](system_workflow.md)**: Detailed step-by-step explanation of ingestion and runtime flows.
*   **[Architecture & Design](architecture.md)**: High-level system design and component breakdown.
*   **[Remaining Tasks](remaining.md)**: Roadmap of pending features and known gaps.
*   **[API Documentation](http://localhost:8000/docs)**: Swagger UI (once server is running).

## 🛠️ Components

### Ingestion Engine (`ingestion/`)
*   `stm32_mcu_ingester.py`: Seeds the database with known MCU part numbers.
*   `st_pmic_ingester.py`, `st_can_ingester.py`, etc.: Specialized seeders for other components.
*   `run_full_ingestion.py`: The main workhorse. Downloads PDFs and runs the `STM32DatasheetExtractor`.
*   `stm32_errata_ingester.py`: Fetches Errata sheets.

### Database (`database/`)
*   **PostgreSQL** schema storage for Parts, Specs, Documents, and Errata.
*   Uses `pgvector` (planned) and standard SQL for parametric search.

### Solver (`solver/`)
*   Constraint satisfaction engine for Pin Muxing and Power Budgeting.

## 💻 Usage

Start the API Server:
```bash
python server.py
```
Access the UI at `http://localhost:8000`.
