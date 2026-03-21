# Silicon-Pilot — Dream Specs Status Tracker

## ✅ DS2: Smart BOM Compatibility Checking — DONE
`POST /api/bom/check` → `solver/bom_checker.py`

Checks:
- Voltage level mismatches (3.3V vs 1.8V IO)
- Power supply adequacy (LDO output vs MCU power draw)
- Interface scaling (number of bus lines vs load)
- CAN transceiver pairing
- Displayed in UI as a cross-component compatibility report with pass/warn/fail per check

## ✅ DS4: AI Peer Review (Architect's Notes) — DONE
`POST /api/peer-review` → `llm/rigorous_explainer.py::generate_architect_review()`

Provides:
- Overkill warnings ("480MHz MCU for a simple logger")
- Missing constraint identification
- Red/Amber/Green verdict
- Thermal dissipation pass/fail for the selected package
- Available on any candidate card (not just the top one)

---

## ❌ DS1: Context-Aware Component Selection — NOT IMPLEMENTED

**What's missing:**
The current ranking engine (`ml/ranking_engine.py`) uses deterministic ML scoring on hardware specs only. It has no awareness of:
- User persona (student vs enterprise)
- Procurement context (1-unit prototype vs 100k volume)
- Ecosystem preference (Arduino-friendly vs bare-metal)
- Supply chain maturity (prefer NRND-free parts)
- Long-term support requirements

**To implement:**
1. Add a `UserContext` model to `core/models.py` with fields: `persona`, `volume`, `risk_tolerance`, `ecosystem`
2. After LLM parses requirements (`/spec/from_text`), run a second structured extraction to fill `UserContext`
3. In the ranking engine, add a `context_score` multiplier that boosts or penalizes candidates based on context signals
4. Expose context editing in the UI so the user can tweak it

---

## ⚠️ DS3: LLM-Driven Config Generation (CubeMX / C Scaffolding) — STUB ONLY

**What exists:**
`architecture/config_generator.py` generates static, rules-based notes about clock tree config, pin assignments, and power budget. No LLM involvement. No `.ioc` file output.

**What's missing:**
- LLM-driven selection of which peripherals go to which pins (currently just static lookups)
- Actual `.ioc` file generation (STM32CubeMX XML format)
- Or alternatively: structured C/C++ HAL initialization code scaffolding
- UI button to download the generated file

**To implement:**
1. Create `llm/config_generator_llm.py` that takes a `RequirementSpec` + selected MCU and asks the LLM to map abstract requirements to specific pin/clock assignments
2. Create `architecture/ioc_writer.py` to translate LLM output into STM32CubeMX `.ioc` XML format
3. Add `POST /api/generate-config` endpoint returning a downloadable `.ioc` file
4. Add a "📥 Download CubeMX Config" button to the UI candidate card
