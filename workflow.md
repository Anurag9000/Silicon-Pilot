HardwareGenius System Workflow
This document details exactly how the system works, linking files, functions, and data flows.

1. Initialization & Ingestion Workflow
Entry Point: 
scripts/run_pipeline.py
 -> 
main()

Step 1: Database Setup
File: 
scripts/setup_database.py
Action: Connects to PostgreSQL, drops existing schema (if requested), and applies database/*.sql files.
Artifacts: Creates tables 
parts
, mcu_specs, ldo_specs, pmic_specs, etc.
Step 2: Component Seeding
Files: 
ingestion/stm32_mcu_ingester.py
, 
st_ldo_ingester.py
, 
st_pmic_ingester.py
, etc.
Function: 
ingest_family(family_name, data)
Action:
Iterates through hardcoded Python dictionaries of families.
Generates MPNs (e.g., 
STM32
 + F405 + R + G + T + 6).
Inserts/Upserts into 
parts
 table.
Inserts/Upserts into specific spec tables (e.g., mcu_specs).
Step 3: Datasheet Acquisition
File: 
ingestion/downloader.py
Function: download_datasheet(url)
Action: HTTP GET to manufacturer URL. Saves PDF to datasheets/ directory. Handles retries and user-agent spoofing.
Step 4: Datasheet Extraction (MCU)
File: 
ingestion/stm32_datasheet_extractor.py
Function: extract_pinout(pdf_path)
Action:
Converts PDF pages to text.
Regex scans for "Table X. Pin definition".
Parses table rows for Pin Name (e.g., "PA9") and Function (e.g., "USART1_TX", "TIM1_CH2").
Updates mcu_specs or a pin definition table (not fully normalized yet in seed).
Step 5: Errata Processing
File: 
ingestion/stm32_errata_ingester.py
Action: Downloads Errata sheets.
File: 
ingestion/stm32_errata_extractor.py
Action: Parses "Workaround" sections and inserts into errata_items.
2. Server & Runtime Workflow
Entry Point: 
server.py

Startup (
lifespan
 context manager)
Database: Initializes asyncpg.create_pool(dsn).
Solvers: Instantiates 
PinMuxSolver(pool)
, 
DesignRuleChecker(pool)
, 
ReferenceDesignMatcher(pool)
.
Web UI: Sets up Jinja2Templates for serving HTML from web_ui/templates.
User Flow A: Parametric Search
Request: GET /api/search?q=STM32F4&flash_min=1024
Handler: server.py:search_parts
Logic:
Constructs SQL query dynamically based on logic in server.py.
Joins parts with relevant spec tables (mcu_specs, ldo_specs, etc.).
Returns JSON list of matching parts.
User Flow B: Intelligent Architecture Builder
Request: POST /api/build-architecture (Payload: "I need a flight controller")
Handler: server.py:build_architecture
Logic:
Intent Parsing: Calls IntentParser (mock or LLM based) to extract requirements (e.g., "Main MCU", "IMU", "Motor Control").
Matching: Calls ReferenceDesignMatcher.find_similar_designs to see if a "Flight Controller" design exists.
Selection: If no match, queries parts for best fits for each block (MCU, Gyro, Regulator).
Validation: Calls DesignRuleChecker.check_power_supply to ensure regulators match MCU voltage.
Response: Returns a JSON structure representing the system blocks and selected parts.
User Flow C: Pin Muxing
Request: POST /api/solve-pinmux (Payload: PartID, Requirements: [UART1, SPI2])
Handler: server.py:solve_pinmux
Logic:
Calls PinMuxSolver.solve(part_id, requirements).
Queries pin definitions from DB.
Runs CSP (Constraint Satisfaction Problem) backtracking to assign pins to functions.
Returns valid pin mapping or error.
3. Key Files Reference
| File | Role | Key Functions | | output | --- | --- | | server.py | Main API & App | lifespan, search_parts, build_architecture | | scripts/run_pipeline.py | Ingestion Master | main | | ingestion/stm32_mcu_ingester.py | Seed Data | ingest_family | | solver/pin_mux_solver.py | Pin Validation | solve | | solver/design_rule_checker.py | Electrical Rules | check_design | | architecture/reference_design_matcher.py | Similarity Engine | find_similar_designs |*