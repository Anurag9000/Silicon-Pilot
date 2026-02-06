---
trigger: always_on
---

as this great engineer pinnacle and mastery you have give prompt i will paste to gemini which has a complete and thorough deep exact instructions of how exactly to go about accomplishing them from programming point of view everything excplicit and stated out clearly
Here’s a **single copy-paste prompt** you can drop into Gemini. It tells Gemini to produce a **complete, programming-level blueprint + code skeleton** for a robust, scalable “engineering-grade hardware recommender” with **evidence-backed specs**, a **deterministic solver**, and an **LLM questioner/orchestrator**.

---

## Prompt to paste into Gemini

You are a senior AI/ML systems engineer and backend architect. Design and specify (at programming depth) a robust, scalable system that recommends electronic components (starting with MCUs) from manufacturer datasheets and product pages, using a deterministic constraint solver and evidence-backed structured data. The system must also support a conversational mode where the AI asks as many counter-questions as needed to refine the user’s requirements, and eventually supports abstract intent like “I want to build a CAN-based motor controller” and derives reasonable subsystem requirements and a BOM.

### Absolute rules (must follow)

1. **LLM is not a source of truth for specs.** All filtering/ranking must use verified structured data extracted from documents and stored with provenance.
2. **Evidence required:** Every spec field used in decisions must have an evidence record (source URL, doc hash, page number/section, and a snippet reference or bounding box).
3. **Deterministic core:** Candidate selection = hard constraints. Ranking = explainable scoring. No “vibes”.
4. **Unlimited questions allowed**, but implement a **question policy**: maximize information gain, batch questions, stop when top-N is stable.
5. **No Dynamic Programming** in algorithms (avoid DP approaches).
6. Produce output that is directly buildable: repo layout, DB schema, APIs, pseudocode AND real code skeletons.

---

# Deliverables you must output (in this order)

## (A) System Overview (1–2 pages)

* What the system does, key user flows:

  * Constraint mode: “need Cortex-M, ≥2 CAN, QFP, –40..85°C…”
  * Intent mode: “I want to build X system…”
* Core principles: deterministic + evidence + human-in-the-loop ingestion.
* What’s in MVP vs v1 vs v2.

## (B) Architecture Diagram (text form) + Services

Describe services and their responsibilities. Include:

1. **Frontend/Web UI** (Requirements Spec editor + evidence viewer + results)
2. **Orchestrator service (LLM controller)**: parses user input, asks questions, compiles a RequirementSpec, calls solver and retrieval
3. **Solver service (deterministic)**: hard filter + ranking + near-miss
4. **Data ingestion pipeline**: fetch docs, parse tables/images, OCR fallback, normalize, validate, store evidence
5. **Review UI / Human-in-loop**: approve/override low-confidence extractions and conflicts
6. **Evidence store**: doc cache, snippets, page coordinates, hashes
7. **Observability**: logs, metrics, tracing

Choose a realistic stack:

* Backend: Python 3.11, FastAPI, Pydantic
* DB: PostgreSQL (with JSONB), optionally pgvector for semantic retrieval of evidence/snippets
* Queue: Redis + Celery (or RQ)
* Storage: local/S3-compatible for PDFs and snippet images
* Containerization: Docker + docker-compose
* Optional: a separate “Document parsing worker” service

## (C) Data Model (Postgres schema)

Provide SQL DDL for tables with indexes. Must include:

* `parts` (mpn, manufacturer, family, status, temp range, package, pin count, etc.)
* `part_specs` (normalized fields OR denormalized JSONB; justify choice)
* `evidence` (field_name, source_url, source_type, doc_hash, page, bbox/snippet_ref, extracted_value, confidence, extracted_at)
* `documents` (url, hash, fetched_at, content_type, versioning)
* `extraction_runs` (run_id, parser_version, success/fail, error)
* `conflicts` (field conflicts across sources, resolution status)
* `templates` (for intent mode: subsystem graphs, questions)
* `queries` and `recommendation_logs` (store RequirementSpec, questions asked, final candidates, ranking reasons)

Include constraints and indexes for:

* fast hard filtering by common fields (flash_kb, ram_kb, can_count, package_family, temp_min/temp_max, status)

## (D) Core Types (Pydantic models)

Define these Pydantic models explicitly:

* `RequirementSpec`

  * hard constraints
  * soft preferences
  * environment/production constraints
  * intent metadata
  * “unknown” fields tracking
* `Question`
* `Answer`
* `CandidatePart`
* `RecommendationResult` (with evidence pointers)

## (E) Ingestion Pipeline (real-world PDF/table/image issues)

Write an exact plan AND code skeleton for ingestion:

1. Fetch manufacturer HTML + official PDF (cache with hash)
2. Parse:

   * Try layout-aware table extraction first
   * Detect image-based tables; OCR fallback
3. Extract:

   * part numbers
   * spec fields with units and ranges
   * ordering-code decoding support (part number suffix parsing rules)
4. Normalize:

   * unit normalization
   * package normalization (QFP variants)
   * synonyms (CAN vs CAN-FD vs vendor naming)
5. Validate:

   * type/range checks
   * cross-source conflict detection
6. Store:

   * structured fields + evidence record per field
7. Review queue:

   * low confidence
   * conflicts
   * distributor-only claims
8. Publish to “trusted” dataset only after passing thresholds

Provide a practical approach to OCR:

* Use a CPU-friendly baseline (e.g., Tesseract) and optionally a “document AI” plug-in interface.
* Include bounding box capture so evidence can be shown.

## (F) Deterministic Solver (hard filter + ranking + near-miss)

Provide exact algorithms and implementable code skeleton:

* `compile_constraints(RequirementSpec) -> SQL WHERE + params`
* `hard_filter(parts_query) -> candidate set`
* `rank(candidates, spec) -> sorted list with score breakdown`
* `near_miss(spec) -> candidates failing exactly 1 hard constraint`

Ranking must be explainable and logged:

* show score components: headroom, ecosystem score (curated), lifecycle risk, availability proxy, etc.
* ensure “hard constraint violation => excluded (unless near-miss mode)”

## (G) Conversational Question Engine (information gain)

Implement a policy:

* identify missing fields that most change candidate set/ranking
* batch questions into Tier 1 / Tier 2 / Tier 3
* stop condition: top-N stable across plausible values OR user chooses “good enough”
* include “why I’m asking” text per question

Provide:

* question selection algorithm (heuristic is fine)
* data structures to track uncertainty
* example conversation traces for:

  1. constraint mode
  2. intent mode

## (H) Intent → Architecture → BOM (v2 path)

Specify a template library system:

* templates stored as YAML/JSON in DB or repo
* each template contains:

  * subsystem graph (compute, power, comms, sensing, protection)
  * default assumptions
  * required questions checklist
  * mapping from answers → constraints

Provide an example template for:

* “CAN-based motor controller”
  It should produce:
* compute constraints (e.g., CAN controllers, PWM timers)
* need for CAN transceiver
* power stage notes (even if not fully recommended yet)
* environmental constraints prompts

## (I) APIs (FastAPI endpoints)

Define endpoints and request/response schemas:

* POST `/spec/parse` (user text → draft RequirementSpec)
* POST `/spec/ask` (RequirementSpec → questions batch)
* POST `/spec/answer` (apply user answers → updated spec)
* POST `/recommend` (RequirementSpec → RecommendationResult)
* GET `/parts/{mpn}`
* GET `/evidence/{evidence_id}`
* POST `/ingest` (admin)
* GET `/review/queue`
* POST `/review/resolve`

## (J) Repo Layout + Code Skeleton (must include actual code)

Output a repository tree and then provide code skeletons for key files:

* `backend/app/main.py` (FastAPI)
* `backend/app/models.py` (Pydantic)
* `backend/app/db.py` (SQLAlchemy/asyncpg)
* `backend/app/solver.py`
* `backend/app/question_engine.py`
* `backend/app/ingestion/` modules:

  * `fetcher.py`, `pdf_parser.py`, `ocr.py`, `extractor.py`, `normalizer.py`, `validator.py`, `publisher.py`
* `workers/ingest_worker.py` (Celery/RQ worker)
* `docker-compose.yml`
* `migrations/*.sql` or Alembic setup
* `tests/` with at least:

  * hard filter correctness
  * evidence-required enforcement
  * near-miss correctness

Code must be minimal but runnable with placeholders. Use clear TODO markers.

## (K) Observability + Quality Gates

Provide:

* logging schema (request_id, spec_id, run_id)
* metrics (invalid recommendation rate must be 0, evidence coverage %, conflict rate)
* regression test strategy with “golden specs”
* CI plan

## (L) Security/Legal Constraints

Include:

* caching strategy and respecting terms/robots
* rate limiting ingestion
* separating “trusted manufacturer sources” vs “untrusted sources”

---

# Output formatting requirements

* Use headings exactly (A) … (L).
* Provide SQL in code blocks.
* Provide Python code in code blocks.
* Provide docker-compose in code blocks.
* Be explicit. No hand-wavy “then do X”.
* Keep assumptions stated clearly.

Now generate the complete system design and code skeleton per the above.
