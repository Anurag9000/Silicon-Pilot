# HardwareGenius System Workflow

## 1. System Initialization & Persistence
- **Database**: PostgreSQL is the single source of truth.
  - **Schema**: Controlled by `schema.sql` (core) and `component_tables.sql` (domain specs).
  - **Connection**: Managed via `DATABASE_URL` env var. The `server.py` uses `asyncpg` to maintain a connection pool.
  - **Persistence**: Because it's Postgres (not in-memory SQLite), data persists as long as the Postgres service is running/storage is intact.

## 2. Data Ingestion Pipeline (The "Truth" Builder)
This process runs offline/background to populate the DB.
1.  **Download**: `ingestion/stm32_downloader.py` fetches PDFs from ST.com.
    -   *Logic*: Iterates known families -> Checks cache -> Downloads if new -> Updates `documents` table.
2.  **Extraction**: `ingestion/run_stm32_ingestion.py` orchestrates the parsing.
    -   **Parsing**: `PDFParser` reads the PDF.
    -   **Metadata**: `FieldExtractor` finds MPNs, Flash, RAM, etc., capturing `bbox` (coordinates) and `page`.
    -   **Evidence**: Snippets are rendered to `data/snippets/{uuid}.png`.
3.  **Storage**:
    -   Basic specs go to `parts` and `mcu_specs`.
    -   Traceability data goes to `evidence` table, linking specific fields to the snippet image path.

## 3. User Interaction Flow (The "v2" Unified Server)
All traffic hits `server.py` (Port 8000).

### A. Intent Analysis
1.  **User**: Enters "Build a CAN motor controller" on the frontend.
2.  **Frontend**: Calls `POST /spec/from_text`.
3.  **Backend**: `LLMOrchestrator` translates text -> structured `RequirementSpec` (JSON).
    -   *Example*: `{ "hard_constraints": { "can_count": 1 }, "unknowns": ["voltage"] }`

### B. Refinement (Question Engine)
1.  **Backend**: Checks `spec.unknowns`. If critical info missing, `QuestionEngine` generates questions.
2.  **Frontend**: Displays questions ("What is the voltage?").
3.  **User**: Answers.
4.  **Backend**: `POST /spec/answer` updates the `RequirementSpec`.

### C. Recommendation (Deterministic Solver)
1.  **Backend**: `HardFilter` executes SQL: `SELECT * FROM parts WHERE can_count >= 1 ...`.
    -   *Crucial*: No LLM hallucination here. Rigid SQL logic.
2.  **Backend**: `RankingEngine` scores candidates (Headroom, Cost, etc.).
3.  **Backend**: Returns `RecommendationResult` with `CandidatePart` objects.

### D. Evidence Presentation
1.  **Frontend**: Renders the card for `STM32F405`.
2.  **User**: Clicks "View Evidence".
3.  **Frontend**: Requests `<img src="/evidence/{id}/content">`.
4.  **Backend**: Serves the `.png` snippet created during ingestion.

## 4. Admin & Ops
- **Ingestion Trigger**: `POST /admin/ingest` (Async background task).
- **Conflict Review**: (Future) UI to manually resolve conflicting data from multiple datasheets.
