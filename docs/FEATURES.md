
# Silicon-Pilot Feature Manifest

This document exhaustively lists every feature, capability, and supported component in the Silicon-Pilot system.

## 1. Component Support
The system currently supports ingestion, search, and validation for the following component categories:

### A. Core Computing (MCU)
*   **STM32 Microcontrollers**: Full support for F, H, L, G, WB, WL, U, C series.
*   **Parametric Data**: Core type (Arm Cortex-M0/M3/M4/M7/M33), Clock Speed (MHz), Flash Size (KB), SRAM Size (KB), EEPROM.
*   **Peripherals**: UART, SPI, I2C, CAN, USB, ADC, DAC, Ethernet.
*   **Electrical**: Min/Max Voltage, Power consumption in Run/Stop modes.
*   **Pin Muxing**: Pin-to-Function mapping (e.g., PA9 -> USART1_TX).

### B. Power Management
*   **LDO Regulators**: 
    - Families: LDL1117, LDK320, LD39015.
    - Specs: Vin, Vout, Iout, Dropout Voltage, PSRR.
*   **DC-DC Converters**:
    - Families: L6984, ST1S10, L7986.
    - Specs: Vin, Vout, Iout, Efficiency, Topology (Buck/Boost).
*   **PMICs**:
    - Families: STPMIC1 (STM32MP1 companion), L4995 (Automotive).
    - Specs: Buck/LDO counts, I2C/SPI control, Automotive Grade.

### C. Communication & Sensors
*   **CAN Transceivers**:
    - Families: L9616, L9966.
    - Specs: Data Rate (Mbps), ESD Protection, Wakeup/Standby modes.
*   **Sensors**:
    - Accelerometers: LIS2DH12.
    - Temperature: STTS751.
    - Specs: Interface (I2C/SPI), Resolution, Sampling Rate.

### D. Passives
*   **Resistors & Capacitors**:
    - Generic BOM placeholders (0402, 0603).
    - Specs: Value, Tolerance, Power/Voltage Rating, Dielectric (X7R, C0G).

## 2. Ingestion Engine Features
*   **Hybrid Seeding**: 
    - Instantly populates the database with ~1000 known parts using Python dictionaries, bypassing slow scraping for initial discovery.
*   **Resilient Downloader**:
    - `downloader.py` handles HTTP retries, user-agent rotation, and session persistence to fetch PDFs from manufacturer sites reliably.
*   **PDF Extraction**: 
    - `stm32_datasheet_extractor.py` uses Regex and layout analysis to scrape tabular data from raw PDFs.
    - Extracts: Pin Definitions, Alternate Functions, Absolute Maximum Ratings.
*   **Errata Processing**:
    - Automatically discovers, downloads, and parses Silicon Errata sheets.
    - Links specific bugs (e.g., "I2C1 limitation") to specific die revisions.

## 3. Engineering Solvers
*   **Pin Mux Solver**:
    - Constraint Satisfaction Problem (CSP) engine.
    - Resolves pin conflicts (e.g., "Can I use USART1 and SPI1 simultaneously on this specific package?").
*   **Design Rule Checker (DRC)**:
    - Validates electrical compatibility.
    - Rules:
        - **Power**: Does the Regulator Vout match the MCU Vin? Is Iout sufficient?
        - **Signal**: Do CAN transceiver voltage levels match the MCU I/O voltage?
*   **Reference Design Matcher**:
    - Uses similarity algorithms (Jaccard Index, Cosine Similarity) to find existing, proven designs that match user requirements.
    - Optimized with SQL `json_agg` for high performance.
*   **Connection Pooling**:
    - All solvers use a shared `asyncpg.Pool` for sub-millisecond database access.

## 4. Server & API Features
*   **Unified Backend**: 
    - Single FastAPI instance serving both REST API and Web UI (Jinja2).
*   **Endpoints**:
    - `GET /api/search`: Multi-criteria filtering.
    - `GET /api/parts/{id}`: Deep dive into a specific part.
    - `POST /api/build-architecture`: AI-driven system block generation.
    - `POST /api/export`: Generates JSON/CSV BOMs.
    - `POST /api/context/ingest`: Accepts new context for LLM agents (if enabled).
## 4. Intelligent Capabilities (LLM-Driven)
*   **Intent Classification**: Maps natural language queries ("I need a low power MCU for a wearable") into structured SQL constraints.
*   **Dynamic Questioning**: Uses LLM to clarify ambiguous requirements by asking targeted follow-up questions.
*   **LLM-Enhanced Template Matching**: Maps high-level design intents to specific system templates with 95% accuracy.
*   **Intelligent Constraint Optimization**: Optimizes peripheral allocations and power/speed headroom based on domain-specific best practices.
*   **Natural Language Explanations**: Provides human-readable justifications for every component recommendation, tailored to the user's expertise level.

## 5. Server & API Features
*   **Parametric Search Interface**: 
    - Sliders and checkboxes for filtering parts.
*   **Architecture Builder**:
    - Visual block diagram generation based on requirements.
*   **Interactive Chat**:
    - Interface for querying the LLM Agent about component selection.

## 6. Verification & Quality
*   **Stress Testing**: `scripts/stress_test.py` validates <5ms API latency.
*   **Integration Testing**: `tests/test_integration.py` validates end-to-end flows for all solvers.
