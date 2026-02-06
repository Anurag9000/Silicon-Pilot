---
trigger: always_on
---

Here’s a **concrete, build-ready spec** with a stack I’d recommend for a robust “engineering-grade” system.

---

## Recommended stack (what I’d ship in industry)

### Backend + core services

* **Python 3.12** (fast iteration, best doc tooling, strong PDF ecosystem)
* **FastAPI** (typed APIs, speed, great DX)
* **PostgreSQL 16** (structured truth + JSONB for extensibility)
* **Redis** (queue + caching)
* **Celery** (or RQ) for ingestion workers
* **S3-compatible object storage** (MinIO locally; S3 in prod) for PDFs + evidence snippets
* **SQLAlchemy 2.0 + asyncpg** (or psycopg3)

### Document extraction

* **PyMuPDF (fitz)** for rendering pages + bbox capture (best practical tool)
* **pdfplumber** for text + table hints
* **Camelot** (stream/lattice) for vector tables
* **Tesseract OCR** as baseline fallback (image tables)
* Optional later: **Layout model** (e.g., docTR / Detectron layout) as a plug-in

### UI

* **Next.js (React)** + Tailwind
* Must-have features: Requirements Spec editor, evidence viewer, recommendation comparison, review queue UI.

This stack minimizes “research-y” risk and maximizes “ships in 8–12 weeks” reality.

---

## System spec (MVP → v1 → v2)

### Goals

1. Deterministic recommendations from structured data.
2. Every decision backed by evidence pointers into documents.
3. Conversational refinement with unlimited counter-questions, but **high information gain** and **stop criteria**.
4. Later: intent → architecture template → BOM.

---

# A) Data contracts (your system’s backbone)

## A1) RequirementSpec (canonical internal format)

**All user input compiles into this.**

**Hard constraints (must)**

* `core`: {Cortex-M0/M3/M4/M7/RISC-V/…}
* `flash_kb_min`
* `sram_kb_min`
* `temp_min`, `temp_max`
* `package_family`: {QFP, BGA, QFN, …}
* `pin_count_range` (optional)
* `peripherals_min`: e.g. `{can:2, uart:2, spi:2, i2c:1, usb:1}`
* `status`: {active_only|allow_nrnd|allow_eol}

**Soft preferences (rank weights)**

* `prefer_can_fd` (bool)
* `prefer_lower_power` (weight)
* `prefer_lower_cost` (weight)
* `prefer_more_headroom` (weight)
* `prefer_vendor` (list/weight)
* `prefer_ecosystem` (weight)

**Context**

* `region` (for availability)
* `volume` (prototype vs production)
* `budget_per_unit` (optional)
* `certification_needs` (optional)

**Uncertainty tracking**

* `unknowns`: list of missing fields
* `assumptions`: explicit assumed values (labeled “assumption” not “fact”)

---

## A2) “Evidence or it didn’t happen” rule

Any field used in:

* hard filtering
* ranking
* explanations
  must have an `EvidenceRecord` attached, unless it’s explicitly an **assumption** (which must be labeled as such and must NOT be used for hard filtering).

---

# B) Database schema (Postgres) — concrete

You want **fast hard filtering** + **traceability**. Use **typed columns for common filters** and **JSONB for extensibility**.

## B1) Tables

### `parts`

* `id` (uuid, pk)
* `mpn` (text, unique, indexed)
* `manufacturer` (text, indexed)
* `family` (text, indexed)
* `status` (enum: active/nrnd/eol/unknown, indexed)
* `package_family` (enum: qfp/qfn/bga/… indexed)
* `package_name` (text) (e.g., LQFP-144)
* `pin_count` (int, indexed)
* `temp_min_c` (int, indexed)
* `temp_max_c` (int, indexed)

### `mcu_specs` (typed, queryable)

* `part_id` (fk -> parts.id, unique)
* `core` (text, indexed)
* `max_mhz` (int)
* `flash_kb` (int, indexed)
* `sram_kb` (int, indexed)
* `can_count` (int, indexed)
* `can_fd_count` (int, indexed)
* `usb_fs` (bool)
* `usb_hs` (bool)
* `ethernet` (bool)
* `spi_count` (int)
* `i2c_count` (int)
* `uart_count` (int)
* `adc_channels` (int)
* `timers_count` (int)
* `extras` (jsonb)  // anything not normalized yet

### `documents`

* `id` (uuid, pk)
* `source_url` (text, unique)
* `source_type` (enum: mfg_pdf/mfg_html/dist_html/other)
* `fetched_at` (timestamptz)
* `doc_hash` (text, indexed)
* `content_type` (text)
* `storage_key` (text) // S3 key
* `version` (int) // increment if URL updated but hash differs

### `evidence`

* `id` (uuid, pk)
* `part_id` (fk)
* `field_path` (text) // e.g., "mcu_specs.flash_kb"
* `extracted_value_raw` (text)
* `normalized_value` (jsonb) // e.g., {"value":2048,"unit":"kb"}
* `document_id` (fk)
* `page` (int)
* `bbox` (jsonb) // {"x0":...,"y0":...,"x1":...,"y1":...} in page coords
* `snippet_storage_key` (text) // image snippet rendered from bbox
* `confidence` (float)
* `parser_version` (text)
* `extracted_at` (timestamptz)

### `conflicts`

* `id` (uuid, pk)
* `part_id` (fk)
* `field_path` (text)
* `evidence_ids` (uuid[]) // conflicting
* `status` (enum: open/resolved/ignored)
* `resolution` (jsonb) // chosen value + reason
* `resolved_by` (text)
* `resolved_at` (timestamptz)

### `requirement_specs`

* `id` (uuid, pk)
* `created_at`
* `spec` (jsonb) // canonical RequirementSpec
* `source_text` (text) // what user typed
* `mode` (enum: constraint/intent)

### `question_turns`

* `id` (uuid, pk)
* `spec_id` (fk)
* `turn_index` (int)
* `questions` (jsonb) // list of Question objects
* `answers` (jsonb) // list of Answer objects
* `created_at`

### `recommendation_logs`

* `id` (uuid, pk)
* `spec_id` (fk)
* `candidates` (jsonb) // mpn list + scores
* `explanations` (jsonb) // score breakdown + constraint checks
* `created_at`

## B2) Indices (critical for speed)

* `parts(manufacturer, status, package_family, pin_count)`
* `parts(temp_min_c, temp_max_c)`
* `mcu_specs(core, flash_kb, sram_kb, can_count, can_fd_count)`
* `evidence(part_id, field_path)`
* `documents(doc_hash)`

---

# C) Ingestion pipeline — concrete and survivable

## C1) Input sources (priority)

1. Manufacturer product page (HTML) if it has param tables
2. Official manufacturer PDF datasheet
3. Ordering info PDF / family reference
4. Distributor pages only for availability/price (never authoritative specs)

## C2) Worker stages (each writes artifacts + logs)

**Stage 1: Fetch**

* download HTML/PDF
* compute hash
* store in S3 + `documents`

**Stage 2: Parse**

* for PDF:

  * render each page to image (PyMuPDF)
  * extract text blocks (pdfplumber)
  * attempt table extraction (Camelot) on likely table pages
  * detect image-table pages (low text density) → OCR path

**Stage 3: Extract**

* identify part numbers (regex + vendor patterns)
* extract spec values:

  * memory (flash, sram)
  * temps
  * package options
  * peripheral counts (CAN, etc.)
* store raw extractions as (field_path, raw_value, evidence bbox/page)

**Stage 4: Normalize**

* convert units, map synonyms, unify package family
* parse part-number suffix encoding (vendor rules modules)

**Stage 5: Validate**

* range/type checks
* internal consistency checks (e.g., temp_min < temp_max)
* cross-source checks: manufacturer vs distributor mismatch opens `conflicts`

**Stage 6: Publish**

* Only publish field into `mcu_specs` when:

  * confidence ≥ threshold (e.g., 0.85), OR
  * manually approved in review UI
* otherwise stays “provisional” (exists only as evidence + pending)

## C3) Human-in-the-loop (real necessity)

A review UI lists:

* low-confidence fields
* conflicts
* missing critical fields (flash, ram, can_count, temp, package)

Reviewer sees:

* datasheet snippet image from bbox
* extracted raw text
* suggested normalized value
  Buttons: approve / edit / reject.

---

# D) Deterministic recommendation core — exact behavior

## D1) Hard filter

Given RequirementSpec:

* generate SQL WHERE clauses on typed columns
* return candidate `part_id`s

**Zero tolerance rule:** a candidate that violates any hard constraint is excluded.

## D2) Ranking (explainable scoring)

Score each candidate with breakdown:

* `headroom_flash = clamp((flash_kb - min_flash_kb)/min_flash_kb)`
* `headroom_ram = clamp((sram_kb - min_sram_kb)/min_sram_kb)`
* `peripheral_margin = can_count - required_can + …`
* `ecosystem_score` (curated per vendor/family, starts manual)
* `lifecycle_score` (active > nrnd > eol)
* optional: `availability_score` (volatile, de-weighted)

Final = weighted sum of these terms.

**Every score term must be shown in explanation.**

## D3) Near-miss mode

Find candidates that fail **exactly one** hard constraint:

* helpful suggestions: “Relax package to QFN” or “Accept –40..105 only”

---

# E) Question engine — unlimited, but disciplined

## E1) Question selection policy (practical)

At each step:

1. Run hard filter with current spec
2. If candidate set is huge or ranking unstable:

   * compute “bottleneck unknowns” (fields that most change results)
3. Ask the smallest set of questions that:

   * shrink candidates drastically, OR
   * stabilize top-N ranking

## E2) Batch questions (tiers)

* **Tier 1 (must answer to be valid)**: package family, temp range, core class, key peripherals
* **Tier 2 (optimization)**: power budget, cost target, ecosystem preference, package pitch limits
* **Tier 3 (future-proofing)**: certification, lifecycle horizon, second-source preference

## E3) Stop criteria (prevents annoyance)

Stop asking when:

* top 10 candidates unchanged under plausible ranges for remaining unknowns, OR
* user clicks “good enough”, OR
* remaining unknowns only affect minor ranking

---

# F) Intent → architecture → BOM (v2 spec)

## F1) Template library

Each template is a JSON/YAML:

* `name`
* `subsystems`: compute, power, comms, sensors, protection
* `required_questions`
* `mapping_rules`: answers → constraints

## F2) Example template: “CAN-based motor controller”

Questions:

* supply voltage (12/24/48?)
* motor type (BLDC/DC/stepper)
* peak current range
* control loop frequency
* environment temp
* comms: CAN2.0 vs CAN-FD
* isolation needed? (yes/no)
* cost ceiling

Outputs:

* compute: needs ≥2 CAN (or CAN+UART), enough PWM timers, ADC channels, DMA
* adds: CAN transceiver, gate driver, current sense, protection (TVS, fuse)
* constraints compiled into RequirementSpec + subsystem BOM slots

Important: BOM items beyond MCUs start as “suggested categories” until you ingest those parts too.

---

# G) APIs (concrete endpoints)

* `POST /spec/from_text`

  * input: `{text, mode}`
  * output: `{spec_id, RequirementSpec, questions_batch}`

* `POST /spec/{spec_id}/answer`

  * input: `{answers: [...] }`
  * output: `{RequirementSpec, next_questions_batch}`

* `POST /recommend`

  * input: `{spec_id}`
  * output: `RecommendationResult` with:

    * ranked candidates
    * constraint check table
    * score breakdown
    * evidence ids for every used field

* `GET /parts/{mpn}`

  * output: structured fields + evidence list

* `GET /evidence/{id}`

  * returns snippet image + metadata (doc URL, page)

* Admin:

  * `POST /ingest` (seed vendor/doc URLs)
  * `GET /review/queue`
  * `POST /review/resolve`

---

# H) Repo layout (practical)

```
/backend
  /app
    main.py
    models.py
    db.py
    solver/
      filter.py
      rank.py
      near_miss.py
    questions/
      policy.py
      tiers.py
    ingestion/
      fetcher.py
      pdf_parse.py
      table_extract.py
      ocr.py
      extract.py
      normalize.py
      validate.py
      publish.py
    admin/
      review.py
  /tests
/docker
  docker-compose.yml
/frontend
  (Next.js app)
```

---

## What I’d build first (the real MVP sequence)

1. **Schema + evidence store** (otherwise you’ll regret it)
2. **MCU-only ingestion for 1–2 vendors** (get end-to-end working)
3. **Hard filter + evidence-required enforcement**
4. **Question engine (Tier 1 + stop criteria)**
5. UI: spec editor + evidence viewer + compare candidates

Only after that: automate ingestion more and expand vendors.

---

If you want, I’ll now output a **true “engineering spec document”** with:

* exact JSON schema for RequirementSpec/Question/Answer/Result
* SQL DDL statements
* ranking formula with default weights
* question selection pseudocode
* ingestion thresholds + validation rules

Say: **“Output the full spec doc + DDL + JSON schemas.”**

