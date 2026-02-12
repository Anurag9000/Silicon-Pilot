# 🛑 MASTER AUDIT CHECKLIST: ALL PENDING WORK

**Scope**: 129+ Files Remaining  
**Objective**: Exhaustive Audit & Fix  
**Instructions**: check off items as they are strictly verified/fixed. Do not check off unless confirmed.

---

## ⚡ Phase 1: Solver Module (Remaining Work)

### Critical & Major Fixes
- [ ] **[pin_mux_solver.py](file:///d:/Done,Toreview/HardwareGenius/solver/pin_mux_solver.py)**: Fix `Unused Constraints` (Line 182) - Implement usage.
- [ ] **[pin_mux_solver.py](file:///d:/Done,Toreview/HardwareGenius/solver/pin_mux_solver.py)**: Fix `Fake Backtracking` (Line 191) - Rewrite as true CSP/Backtracking.
- [ ] **[alternative_suggester.py](file:///d:/Done,Toreview/HardwareGenius/solver/alternative_suggester.py)**: Implement Pricing/Availability data (TODOs).
- [ ] **[design_rule_checker.py](file:///d:/Done,Toreview/HardwareGenius/solver/design_rule_checker.py)**: Fix `Bad Table Reference` (Line 289) - `passive_specs.component_type`.

### Minor Fixes & Improvements
- [ ] **[ml_ranking.py](file:///d:/Done,Toreview/HardwareGenius/solver/ml_ranking.py)**: Rename to `heuristic_ranking.py` OR implement actual ML model.
- [ ] **[near_miss.py](file:///d:/Done,Toreview/HardwareGenius/solver/near_miss.py)**: Implement actual near-miss logic (currently returns top N).
- [ ] **[solver/__init__.py](file:///d:/Done,Toreview/HardwareGenius/solver/__init__.py)**: Review exports.

### Subsystems (New)
- [ ] `solver/subsystems/additional_solvers.py`
- [ ] `solver/subsystems/db_integration.py`
- [ ] `solver/subsystems/multi_solver.py`

### Logic Verification Tasks
- [ ] **[power_budget_calculator.py](file:///d:/Done,Toreview/HardwareGenius/solver/power_budget_calculator.py)**: Verify P=VI formulas and battery derating factors.
- [ ] **[design_rule_checker.py](file:///d:/Done,Toreview/HardwareGenius/solver/design_rule_checker.py)**: Verify rules against industry standards (IPC/JEDEC).
- [ ] **[compiler.py](file:///d:/Done,Toreview/HardwareGenius/solver/compiler.py)**: Verify compilation logic for edge cases.

---

## 📥 Phase 2: Ingestion Module (34 Files)

**Goal**: Verify data extraction accuracy and schema compliance.

### PDF & Text Extraction
- [ ] **[stm32_datasheet_extractor.py](file:///d:/Done,Toreview/HardwareGenius/ingestion/stm32_datasheet_extractor.py)**: Verify PDF parsing & regex patterns.
- [ ] **[pdf_parser.py](file:///d:/Done,Toreview/HardwareGenius/ingestion/pdf_parser.py)**: audit error handling for malformed PDFs.
- [ ] **[extractor.py](file:///d:/Done,Toreview/HardwareGenius/ingestion/extractor.py)**: Verify base extraction logic.
- [ ] `multi_language_extractor.py`: Check support for non-English datasheets.
- [ ] `ordering_code_parser.py`: Verify parsing of complex MPNs.

### Component Ingesters (Verify normalization & DB insertion)
- [ ] `st_can_ingester.py`
- [ ] `st_dcdc_ingester.py`
- [ ] `st_ldo_ingester.py`
- [ ] `st_passive_ingester.py`
- [ ] `st_pmic_ingester.py`
- [ ] `st_sensor_ingester.py`
- [ ] `stm32_mcu_ingester.py`
- [ ] `ti_adc_ingester.py`
- [ ] `ti_mcu_ingester.py`
- [ ] `component_ingesters/dcdc_ingester.py`
- [ ] `component_ingesters/ldo_ingester.py`
- [ ] `component_ingesters/pmic_ingester.py`

### Infrastructure
- [ ] **[downloader.py](file:///d:/Done,Toreview/HardwareGenius/ingestion/downloader.py)**: Audit retry logic and rate limiting.
- [ ] **[fetcher.py](file:///d:/Done,Toreview/HardwareGenius/ingestion/fetcher.py)**: Check HTTP client configuration.
- [ ] `publisher.py`: Verify data publication pipeline.
- [ ] `normalizer.py`: Validate unit conversion (e.g., uA to A).
- [ ] `batch_ingestion.py`: Check batch processing stability.

### Individual Ingestion Scripts
- [ ] `run_full_ingestion.py`
- [ ] `run_targeted_ingestion.py`
- [ ] `run_stm32_ingestion.py`
- [ ] `run_errata_processing.py`
- [ ] `run_component_ingestion.py`

---

## 🗄️ Phase 3: Core Module (6 Files)

**Goal**: Ensure database integrity and robust data models.

- [ ] **[database.py](file:///d:/Done,Toreview/HardwareGenius/core/database.py)**: Audit connection pooling, timeouts, and reconnect logic.
- [ ] **[db_operations.py](file:///d:/Done,Toreview/HardwareGenius/core/db_operations.py)**: **CRITICAL**: Check for SQL injection vulnerabilities.
- [ ] **[models.py](file:///d:/Done,Toreview/HardwareGenius/core/models.py)**: Verify data models match current DB schema.
- [ ] `ontology.py`: Verify relationship definitions.
- [ ] `mock_database.py`: Ensure mock parity with real DB.
- [ ] `__init__.py`: Check exports.

---

## 🏗️ Phase 4: Architecture Module (9 Files)

- [ ] **[architecture_builder.py](file:///d:/Done,Toreview/HardwareGenius/architecture_builder.py)**: Verify system composition logic.
- [ ] `bom_composer.py`: Audit BOM generation accuracy.
- [ ] `compiler.py`: Verify architecture compilation.
- [ ] `config_generator.py`: Check configuration export.
- [ ] `cost_optimizer.py`: Verify cost minimization algorithms.
- [ ] `enhanced_exports.py`: Check export formats (JSON, CSV, BOM).
- [ ] `firmware_stack_recommender.py`: Verify logic.
- [ ] `intelligent_optimizer.py`: Audit optimization convergence.
- [ ] `reference_design_matcher.py`: Verify matching logic.

---

## 🔍 Phase 5: Filtering Module (4 Files)

- [ ] `constraint_parser.py`: Verify parsing of complex user queries.
- [ ] `parametric_filter.py`: Audit filtering efficiency.
- [ ] `ranking.py` (Filtering version): Compare with solver/ranking.py.
- [ ] `__init__.py`

---

## 🧠 Phase 6: LLM & ML Modules (6 Files)

- [ ] `llm/embeddings.py`: Verify vector generation.
- [ ] `llm/rag_engine.py`: Audit retrieval logic and prompts.
- [ ] `llm/prompt_templates.py`: Review prompts for clarity/safety.
- [ ] `ml/recommender.py`: Verify collaborative filtering.
- [ ] `questions/question_parser.py`
- [ ] `questions/semantic_search.py`

---

## 🌐 Phase 7: API & Server (4 Files)

- [ ] **[server.py](file:///d:/Done,Toreview/HardwareGenius/server.py)**: Security audit (CORS, Middleware, Error Handling).
- [ ] **[routes.py](file:///d:/Done,Toreview/HardwareGenius/api/routes.py)**: Verify all endpoints, input validation.
- [ ] `api/__init__.py`
- [ ] `llm_agent.py`: Verify agent loop logic.

---

## 🧪 Phase 8: Tests (36 Files)

**Goal**: Ensure all tests pass and have high coverage.

### Root Tests
- [ ] `tests/conftest.py`
- [ ] `tests/golden_scenarios.json`
- [ ] `tests/test_comprehensive_verification.py`
- [ ] `tests/test_drc_exec.py`
- [ ] `tests/test_exhaustive_api.py`
- [ ] `tests/test_golden_scenarios.py`
- [ ] `tests/test_hard_filter.py`
- [ ] `tests/test_integration.py`
- [ ] `tests/test_intelligent_optimizer.py`
- [ ] `tests/test_matcher.py`
- [ ] `tests/test_ranking.py`
- [ ] `tests/test_real_ingestion.py`
- [ ] `tests/verify_all_features.py`

### Integration Tests (`tests/integration/`)
- [ ] `test_agent_tools.py`
- [ ] `test_ingest_search_flow.py`
- [ ] `test_server.py`

### Unit Tests (`tests/unit/`)
- [ ] `test_ai_search.py`
- [ ] `test_coverage_gap_filler.py`
- [ ] `test_crawler.py`
- [ ] `test_crawler_loop.py`
- [ ] `test_indexer.py`
- [ ] `test_ingest_docs_cli.py`
- [ ] `test_ingestion.py`
- [ ] `test_ingestion_extended.py`
- [ ] `test_integrity_extended.py`
- [ ] `test_llm_agent.py`
- [ ] `test_rag.py`
- [ ] `test_ranking.py` (Unit version)
- [ ] `test_search_agent.py`
- [ ] `test_search_agent_cli.py`
- [ ] `test_search_agent_extended.py`
- [ ] `test_searching_extended.py`
- [ ] `test_storage.py`
- [ ] `test_tools.py`
- [ ] `test_utilities_extended.py`
- [ ] `test_verification_extended.py`

---

## 📜 Phase 9: Scripts (20 Files)

- [ ] `scripts/apply_errata.py`
- [ ] `scripts/apply_ldo_schema.py`
- [ ] `scripts/apply_sql.py`
- [ ] `scripts/collect_stm32_datasheets.py`
- [ ] `scripts/download_all_stm32_docs.py`
- [ ] `scripts/exhaustive_crawler.py`
- [ ] `scripts/full_reset.py`
- [ ] `scripts/ingest_datasheets.py`
- [ ] `scripts/init_complete_database.py`
- [ ] `scripts/kill_server.ps1`
- [ ] `scripts/populate_firmware_stacks.py`
- [ ] `scripts/populate_reference_designs.py`
- [ ] `scripts/run_pipeline.py`
- [ ] `scripts/seed_test_pins.py`
- [ ] `scripts/setup_database.py`
- [ ] `scripts/setup_postgres.py`
- [ ] `scripts/stress_test.py`
- [ ] `scripts/validate_templates.py`
- [ ] `scripts/verify_schema.py`

---

## 🖥️ Phase 10: Web UI (5 Files)

- [ ] `app.py`: Verify UI logic.
- [ ] `demo_app.py`: Check demo functionality.
- [ ] `ui_components.py`: Audit component reusability.
- [ ] `static_server.py`
- [ ] `__init__.py`

---

## 🔄 Final Verification

- [ ] **Multi-Branch Sync**: Apply all fixes to all repository branches.
- [ ] **Full Regression Test**: Run all tests.
- [ ] **Documentation Update**: Update README/API docs.
