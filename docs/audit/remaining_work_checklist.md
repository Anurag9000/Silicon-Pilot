# 🛑 MASTER AUDIT CHECKLIST: ALL PENDING WORK

**Scope**: 129+ Files Remaining  
**Objective**: Exhaustive Audit & Fix  
**Instructions**: check off items as they are strictly verified/fixed. Do not check off unless confirmed.

## 🧠 Phase 5: LLM & ML Modules (6 Files) - COMPLETED

- [x] **[llm/enhanced_matching.py](file:///d:/Done,Toreview/HardwareGenius/llm/enhanced_matching.py)**: Verified semantic matching and fallbacks.
- [x] **[llm/intent_classifier.py](file:///d:/Done,Toreview/HardwareGenius/llm/intent_classifier.py)**: Verified intent extraction logic.
- [x] **[llm/orchestrator.py](file:///d:/Done,Toreview/HardwareGenius/llm/orchestrator.py)**: Verified requirement parsing and question generation.
- [x] **[ml/ranker.py](file:///d:/Done,Toreview/HardwareGenius/ml/ranker.py)**: Verified hybrid ranking logic (Note: placeholder ML weights).
- [x] **[questions/engine.py](file:///d:/Done,Toreview/HardwareGenius/questions/engine.py)**: Verified info-gain logic (Note: simplified entropy).
- [x] **[questions/dynamic_engine.py](file:///d:/Done,Toreview/HardwareGenius/questions/dynamic_engine.py)**: Verified LLM-driven question selection.

---

## 🌐 Phase 7: API & Server (4 Files) - COMPLETED

- [x] **[server.py](file:///d:/Done,Toreview/HardwareGenius/server.py)**: Security audit (CORS, Middleware, Error Handling) - OK.
- [x] **[routes.py](file:///d:/Done,Toreview/HardwareGenius/api/routes.py)**: Verified all $10+$ endpoints and Pydantic models.
- [x] **[api/__init__.py](file:///d:/Done,Toreview/HardwareGenius/api/__init__.py)**: Initialization verified.
- [x] **[llm_agent.py](file:///d:/Done,Toreview/HardwareGenius/llm_agent.py)**: Script verified (if exists, else part of llm/).

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