---
trigger: always_on
---

you are an expert in ai ml systems engineering
Plan how to exactly go about doing this thoroughly
Account for the real world challenges and issues faced
most of the data would be in some diagram or tabular format actually check a few datasheets and stuff where we would be fetching it from

also remember in the end the goal was to later on to move towards a fully automated style system which obviously when the user enters more info the more detailed the better the reccomendation would be but in essence the user could enter something as abstract as "i want to make so and so system"  then the ai would itself think about all the configerations and stuff required reasonably

ChatGPT said:
I’ll lay out a concrete end-to-end architecture and build plan (MVP → robust v1 → “abstract intent → full BOM” v2), then I’ll sanity-check real datasheets to show what extraction actually looks like and where it breaks.


Thought for 1m 30s
What you’re building (in one line)
A deterministic constraint solver + ranked recommender over a clean, structured parts database, with an LLM used for (1) requirement parsing, (2) clarification questions, (3) trade-off explanation, and (4) traceable citations—not as the source of truth.

Phase 0 — Define the “contract” of the system (prevents chaos later)
0.1 Output contract (what the user gets)
For every recommendation, output must include:

Candidate list (e.g., top 10)

Why it matches (constraint-by-constraint)

What it fails (if it’s a near-miss)

Trade-off notes (why #2 is below #1)

Evidence: datasheet page/section pointers (and ideally a saved snippet)

This “evidence requirement” is what stops hallucinations from ever being acceptable.

0.2 Internal contract (what your engine consumes)
You need a normalized schema that captures:

Hard constraints: must satisfy (e.g., ≥512KB Flash, ≥2 CAN, QFP, –40..85°C)

Soft preferences: scoring (e.g., prefer lower cost, lower power, higher headroom)

Context constraints: availability, package assembly, compliance, ecosystem, toolchain

Phase 1 — Data: build a trustworthy part “source of truth”
1.1 You cannot start from PDFs only
Datasheets are inconsistent, tables move, and product families encode details in part-number suffixes. Example: ST’s STM32F7 family uses an ordering scheme where pin count, flash size, package, temperature range are encoded in the part number (you must parse it), not always presented as a simple “Flash=2MB” row. 

1.2 Data sources (in priority order)
Manufacturer product pages + parametric tables (often semi-structured HTML)

Reference manuals / family datasheets (feature superset, caveats)

Ordering information tables (exact sellable SKUs)

Distributor data (availability/price; never authoritative for specs)

Real-world proof: we pulled a PDF for ATSAME70Q21B-AN that’s clearly a third-party “datasheet” wrapper (not Microchip’s canonical datasheet PDF), even though it contains real specs. This is exactly why you need provenance checks. 

1.3 Provenance & trust scoring (non-negotiable)
Every extracted fact gets:

source_url, source_type (manufacturer PDF, manufacturer HTML, distributor HTML, etc.)

timestamp

confidence

proof (page number + bounding box or snippet hash)

Rules:

Manufacturer domain wins over everything.

Distributor-only facts are “provisional” unless confirmed from manufacturer docs.

Phase 2 — Schema design: the minimum viable data model (MCU-first)
Start with MCUs only (tight scope, high value). Expand later to PMICs, sensors, radios, etc.

2.1 Core MCU tables
Part

mfg, mpn, family, status (active/NRND/EOL), temp_grade, package, pin_count

Memory

flash_kb, sram_kb, eeprom_kb, tcm_kb, etc.

Peripherals

can_count, can_fd_count, usb_fs, usb_hs, ethernet, sdmmc, spi_count, …

Electrical

vdd_min, vdd_max, io_voltage_ranges, power_modes (often partial!)

Evidence

link each field to 1+ evidence records

2.2 “Feature is tricky” normalization
You must normalize synonyms and ambiguous labels:

CAN vs CAN-FD vs “M_CAN”

“QFP”, “LQFP”, “TQFP” treated as package family with variants

“Industrial” temp might mean –40..85 or –40..105 depending on vendor

Phase 3 — Ingestion: how you actually extract datasheet data (the ugly reality)
3.1 What extraction looks like in real PDFs
Case A: Clean table on first page (easy)
TI’s SN74HC595 has a “Device Information” table right on page 1 (Part number / package / body size). That’s trivial to parse and cite. 

Case B: Packaging details split into a separate addendum (annoying)
TI also has a separate “Package materials information” section with tape/reel box dimensions and device/package mapping—different structure, different document section. Your pipeline must know this exists. 

Case C: Family datasheet gives lists, not per-MPN structured specs
ST’s STM32F765xx datasheet “Device summary” is basically which part numbers exist (a list), not a clean “MPN → Flash/RAM/peripherals” record. 

Then the “Ordering information scheme” tells you how to decode the suffixes (pins, flash size, package, temperature). 

So: you often need (datasheet + ordering scheme + a SKU table elsewhere) to get complete structured facts.

Case D: Big ordering tables exist, but they’re not the whole story
NXP’s LPC546xx has a huge “Ordering information” table listing type numbers and packages. Great—but peripherals, speed grades, and variants may live elsewhere. You must join across sections. 

3.2 Practical extraction pipeline (works in real life)
Implement as a staged ETL:

Document acquisition

Prefer manufacturer HTML + official PDFs

Cache locally; version every file (hash)

PDF parsing

Try “layout-aware text table extract” first (works for many)

If tables are embedded as images → OCR fallback (document AI / vision)

Capture page number + coordinates for evidence

Entity + field extraction

Extract candidate mpn strings

Extract attribute values with units + ranges

Convert to normalized units (KB, MHz, V, °C)

Validation

Type checks (e.g., temp_min < temp_max)

Cross-check duplicates across sources

Flag conflicts for review

Human-in-the-loop review queue

Any low-confidence field, any conflict, any distributor-only claim

This is how you keep your system “engineering-grade.”

Phase 4 — Recommendation engine (deterministic core)
4.1 Hard filter first (constraint satisfaction)
Example hard constraints:

package family ∈ {QFP variants}

temp_min <= -40 and temp_max >= 85

can_count >= 2

flash_kb >= 512

ram_kb >= 128

status == “active” (or “recommended for new designs”)

This outputs a set of valid parts.

4.2 Rank second (multi-objective scoring)
Score each part using weighted terms:

headroom = (flash - min_flash) + (ram - min_ram) + extra peripherals

power suitability (if you have data)

ecosystem score (SDK maturity, debugging, tooling)

availability proxy (optional, via distributor data)

Important: explain ranking in human terms, but never violate the hard constraints.

4.3 “Near-miss” mode
Users love this: show parts that fail one constraint and tell them exactly what to relax.
It dramatically improves UX and makes the system feel intelligent.

Phase 5 — LLM layer (what it does, and what it must never do)
5.1 LLM responsibilities
Parse user intent → structured constraints

Ask clarifying questions when constraints are under-specified

Map synonyms (e.g., “automotive temp” → –40..125)

Explain tradeoffs and why the top picks differ

Generate a reproducible “constraint spec” that the deterministic engine runs

5.2 LLM must NOT be allowed to:
invent specs

recommend a part that fails hard constraints

cite without a stored evidence pointer

You enforce this with:

tool/function calling

schema validation

“evidence-required” output rules

Phase 6 — The “abstract ask → full configuration” future (your automation goal)
You want:

“I want to build X system” → AI derives reasonable architecture + parts + configs

That’s doable, but you need a design knowledge layer between “intent” and “parts”.

6.1 Build a “Design Template Library”
Create templates like:

“Battery-powered BLE sensor node”

“CAN-based motor controller”

“LoRaWAN remote logger”

“Edge vision camera”

“Smart home gateway”

Each template produces:

subsystems (compute, power, comms, sensors, storage, protection)

interfaces (I2C/SPI/UART, CAN, USB, etc.)

constraints (power budget, temp, enclosure, certification hints)

default choices (reasonable starting point)

6.2 Use stepwise refinement (prevents nonsense)
Pipeline:

User intent → pick template(s)

Ask 5–10 high-leverage questions (environment, power source, comms range, cost, size, sensors, safety)

Compile a formal requirement spec (machine-readable)

Run per-subsystem recommenders (MCU, radio, PMIC, etc.)

Compose a BOM + “why” + alternatives

This is how you go from “abstract” to “automated” without hallucinating.

Phase 7 — Real-world failure modes you must plan for
Specs missing / ambiguous in datasheets (power, exact peripheral counts, errata)

Family vs SKU mismatch (family datasheet says “up to X”, SKU may not have it)

Part-number encoding complexity (suffixes carry meaning) 

Package naming inconsistencies (QFP variants, body size, pitch differences)

Supply chain volatility (availability changes weekly; don’t hardcode)

Licensing / scraping constraints (respect vendor/distributor terms)

Keeping data updated (new revisions, NRND transitions, renamed SKUs)

Phase 8 — Evaluation: how you prove it works
8.1 Golden test suite (mandatory)
Create 50–200 “requirements → expected valid set” test cases:

derived from real projects + professor’s examples

include tricky constraints (temp + package + interfaces)

include “near-miss” expectations

8.2 Metrics
Constraint correctness: 0 invalid parts allowed

Recall: does it find what a human would find?

Ranking quality: top-3 overlap with expert picks

Evidence coverage: % of fields with manufacturer evidence

A practical build order (so you actually finish)
MVP (2–3 weeks):

MCU-only

2–3 vendors

Manual + semi-automatic ingestion

Hard filter + basic scoring

Evidence links stored (page/section)

v1 (next 4–6 weeks):

Automated ingestion pipeline

Conflict resolution + review queue

“Near-miss” explanations

Availability integration (optional)

v2 (“abstract intent”):

10–20 design templates

Stepwise questioning + spec compiler

Multi-subsystem BOM generator

One sharp takeaway from the datasheets we looked at
Even in just a few examples, data lives in multiple shapes:

clean tables (easy) 

separate packaging addenda (annoying)

family lists + encoded ordering schemes (requires decoding)

giant ordering tables that still need joins (not enough alone)