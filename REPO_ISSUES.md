# Repository Findings Log

This file is a running list of concrete problems found during code review.
It is not a design spec. It should be appended to as more issues are verified.

## High Severity

### 1. Search API queries non-existent columns
- File: [`api/routes.py`](api/routes.py)
- Problem: The component search endpoint selects `p.category` and `m.max_freq_mhz`.
- Why it is wrong: The current schema defines `parts.family` and `mcu_specs.max_mhz`, not those column names.
- Impact: `/api/v1/search` will fail or return broken results against the real schema.

### 2. Recommendation flow uses stale/incorrect response fields
- File: [`server.py`](server.py)
- Problem: The recommendation endpoint builds `RecommendationResult` with fields like `total_candidates`, `constraint_checks`, and `near_miss_suggestions`.
- Why it is wrong: The model in [`core/models.py`](core/models.py) expects `total_parts_in_db`, `parts_after_hard_filter`, `constraint_summary`, `ranking_explanation`, and `near_miss`.
- Impact: Response validation will fail or the endpoint will return a 500.

### 3. Recommendation flow may pick the wrong ID from joined rows
- File: [`core/db_operations.py`](core/db_operations.py)
- Problem: `SELECT p.*, m.*` is used in part lookup methods.
- Why it is wrong: The join returns duplicate key names like `id`, `created_at`, and others. Converting that row to a dict loses one side of the collision.
- Impact: Downstream code can read the wrong `id` or overwrite part fields with spec fields.

### 4. Filtering package is not importable as written
- Files:
  - [`filtering/constraint_parser.py`](filtering/constraint_parser.py)
  - [`filtering/parametric_filter.py`](filtering/parametric_filter.py)
  - [`filtering/ranking.py`](filtering/ranking.py)
- Problem: These modules import `hardware_db.models`.
- Why it is wrong: No `hardware_db` package exists in this repository.
- Impact: Importing any of these modules raises `ModuleNotFoundError` immediately.

### 5. Production web UI calls old APIs that no longer exist
- File: [`web_ui/production_app.py`](web_ui/production_app.py)
- Problem: It calls `IntentParser(use_llm=True)` and `parser.parse_intent(...)`.
- Why it is wrong: [`llm/intent_classifier.py`](llm/intent_classifier.py) defines `IntentParser(api_key=None, model="gpt-4")` and exposes `classify(...)`, not `parse_intent(...)`.
- Impact: The parse-intent route is broken.

### 6. Production web UI builds architecture with wrong constructors/methods
- File: [`web_ui/production_app.py`](web_ui/production_app.py)
- Problem: It calls `ArchitectureBuilder()` with no template and later `compiler.compile_constraints(...)`.
- Why it is wrong: [`architecture/compiler.py`](architecture/compiler.py) requires a `DeviceTemplate` in `ArchitectureBuilder.__init__`, and `ConstraintCompiler` exposes `compile(...)`, not `compile_constraints(...)`.
- Impact: The build-architecture path is broken.

### 7. Mock database is missing tables and columns used by the persistence layer
- File: [`core/mock_database.py`](core/mock_database.py)
- Problem: The mock schema omits `question_turns`, `updated_at` on `requirement_specs`, and several fields expected by writes.
- Why it is wrong: [`core/db_operations.py`](core/db_operations.py) inserts/updates `question_turns` and updates `requirement_specs.updated_at`.
- Impact: Mock mode will fail for question flows and some spec updates.

## Medium Severity

### 8. LDO constraint mappings point at the wrong column names
- File: [`solver/compiler.py`](solver/compiler.py)
- Problem: It maps `dropout` to `l.dropout_voltage_mv` and `noise` to `l.output_noise_uv`.
- Why it is wrong: The LDO schema defines `dropout_voltage_v` and `noise_uv_rms`.
- Impact: LDO constraint compilation generates invalid SQL.

### 9. Design-rule checks assume passive fields that do not exist in the active schemas
- File: [`solver/design_rule_checker.py`](solver/design_rule_checker.py)
- Problem: It checks `passive_specs.component_type` and `passive_specs.resistance_ohm`.
- Why it is wrong: The mock schema uses `type` and `value_primary`; the older passive schema also uses `type`/`value_primary`.
- Impact: CAN termination and pull-up checks will fail in mock or legacy schemas.

### 10. Reference design matcher depends on tables that are not obviously provisioned in the active schema
- File: [`architecture/reference_design_matcher.py`](architecture/reference_design_matcher.py)
- Problem: It assumes `reference_designs` and `reference_design_parts` exist.
- Status: The repository does contain a matching schema file, but any environment that does not apply it will fail at runtime.
- Impact: Search and recommendation paths for reference designs are schema-dependent and fragile.

## Notes

- This is a live findings file. Add new verified issues here instead of only in chat.
- If a problem is confirmed to be intentional or already fixed elsewhere, mark it and keep the note for traceability.
