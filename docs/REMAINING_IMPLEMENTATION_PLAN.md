# Silicon-Pilot: Remaining Implementation Plan

Based on a comprehensive review of the codebase and documentation, the following features remain to be completely, fully, and end-to-end implemented. These form Phase 2 (Part B) and Phase 3 of the hardware recommendation intelligence pipeline.

## 1. Context-Aware Component Selection
**Status**: Unimplemented  
**Goal**: Re-rank or override deterministic ML/heuristic rankings based on qualitative user context (Budget sensitivity, Team Expertise, Project Timeline, Expected Volume).

**Step-by-Step Implementation**:
1. **Model Updates**: Add a `UserContext` schema in `core/models.py` to capture context variables.
2. **Selector Class**: Create `solver/context_aware_selector.py` with a `ContextAwareSelector` class.
3. **LLM Integration**: Implement the prompt defined in the roadmap to feed the top 5-10 deterministically ranked candidates into the LLM.
4. **Re-ranking Logic**: Parse the JSON output (`primary_choice`, `alternatives`, `context_match_score`) and replace the default ranked order.
5. **API Integration**: Update `server.py` `/api/recommend` to accept user context and invoke this selector before finalizing the response.

## 2. Smart BOM Compatibility Checking
**Status**: Unimplemented  
**Goal**: Deep, cross-component compatibility validation (Thermal constraints, electrical interfacing, signal overlaps, missing passives like bootstrap capacitors).

**Step-by-Step Implementation**:
1. **Module Creation**: Create `architecture/smart_compatibility.py`.
2. **LLM Analysis Pipeline**: Implement a prompt that injects the complete BOM output from `ArchitectureCompiler` + `BOMComposer`.
3. **Structured Checking**: Ask the LLM to review:
   - *Electrical*: Power sequencing, voltage level translation, current budgets.
   - *Thermal*: Expected heat dissipation vs package capability.
   - *PCB Layout*: Traces, component proximity, missing basic passives.
4. **Report Generation**: Output a structured `CompatibilityReport` containing `issues` (Severity: Critical/Warning/Info) and `suggestions`.
5. **UI Endpoint**: Add `/api/check-bom` to `server.py` and expose the warnings in the frontend before the user downloads the BOM.

## 3. LLM-Driven Configuration Generation (CubeMX Integration)
**Status**: Partially Implemented (Deterministic static stubs exist in `config_generator.py`)  
**Goal**: Use LLM intelligence to map abstract pin assignments and power modes into concrete STM32CubeMX `.ioc` files or detailed firmware scaffolding.

**Step-by-Step Implementation**:
1. **Refactor Generator**: Update `architecture/config_generator.py` to incorporate an LLM client (or create `llm_config_generator.py`).
2. **Context Assembly**: Feed the solved Pin Mux assignments (`PinMuxSolver`), selected Firmware Stack, and `RequirementSpec` into the LLM.
3. **Output Formatting**: Prompt the LLM to output valid `.ioc` configuration text (e.g., `Mcu.Pin0=PA0-ADC1_IN0`).
4. **Validation**: Run a syntax check on the generated `.ioc` text.
5. **Export Expansion**: Hook this into `architecture/enhanced_exports.py` so the user can download a fully functional `.ioc` file directly.

## 4. Design Review and Suggestions (AI Peer Review)
**Status**: Unimplemented  
**Goal**: A final architectural "Peer Review" pass that evaluates the entire system from a high level.

**Step-by-Step Implementation**:
1. **Reviewer Engine**: Create `llm/design_reviewer.py`.
2. **Multi-shot Prompting**: Use the LLM to simulate a Senior Hardware Engineer reviewing the generated design against common real-world failures (e.g., "You selected a 480MHz MCU for a simple environmental logger, this is overkill").
3. **Integration**: Automatically trigger this review alongside the BOM generation and display an "Architect's Notes" section in the final output.

## 5. Learning from User Feedback
**Status**: Unimplemented  
**Goal**: Create an active feedback loop where user adjustments (e.g., rejecting a suggested MCU for cost) are stored and used to fine-tune future recommendations.

**Step-by-Step Implementation**:
1. **Database Schema**: Add a `user_feedback` table in `database/schema.sql` tracking `(session_id, part_id, action (accepted/rejected), reason_text)`.
2. **API Endpoint**: Add `/api/feedback` to `server.py`.
3. **Weight Adjustment**: Create an offline job `ml/feedback_trainer.py` that periodically analyzes rejected components and adjusts the optimization weights in `solver/ranking.py` (e.g., heavily weighting cost down if consistently rejected for budget reasons).

## 6. End-to-End RAG Q&A Integration
**Status**: Core RAG scripts exist, but UI/API integration is incomplete.  
**Goal**: Allow users to ask natural language questions about the selected components directly within the UI, pulling from the embedded datasheet database.

**Step-by-Step Implementation**:
1. **Vector DB Hookup**: Ensure ChromaDB or `pgvector` queries are active in `server.py` under a `/api/chat` or `/api/ask` endpoint.
2. **Contextual Chat**: Pass the current `part_id` and design context into the RAG prompt so queries like "What is the max voltage on pin 14?" are grounded correctly.
3. **UI Hookup**: Add a chat pane to the `web_ui/` that queries this endpoint.

---

### Executing This Plan
To implement these steps, we will proceed chronologically:
1. **Sprint 1**: Context-Aware Selection & Smart BOM Checking (Immediate value to recommendation quality).
2. **Sprint 2**: LLM Configuration (.ioc) & Design Review (Export & Verification value).
3. **Sprint 3**: Feedback Loop & RAG Chat Integration (Continuous improvement and UX).
