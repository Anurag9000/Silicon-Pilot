
# HardwareGenius: The Complete Architecture Guide

This document explains the end-to-end flow of the HardwareGenius system, detailing how it transforms unstructured PDF datasheets into a structured, queryable database effectively used by solvers.

---

## 🏗️ 1. Block Diagram & System Flow

The system operates in two distinct phases: **Offline Ingestion** (Building the Brain) and **Online Serving** (Answering User Design Queries).

![System Architecture Diagram](architecture_flow_diagram.png)

```mermaid
graph TD
    %% Offline Layer
    subgraph "Phase 1: Knowledge Ingestion (Offline)"
        Internet[ST.com / Octopart] 
        
        Crawler[Discovery Engine] -->|1. List Families| PartsTable[Parts Table (MPNs)]
        PartsTable -->|2. URLs| Downloader[Robust Downloader]
        
        Downloader -->|3. PDFs| PDFStore[Datasheet Storage]
        
        PDFStore -->|4. Parse| Extractor[Deep Extractor]
        
        Extractor -->|Pin Definitions| DB_Pins[Table: mcu_pin_functions]
        Extractor -->|Power Specs| DB_Power[Table: power_modes]
        Extractor -->|Peripherals| DB_Specs[Table: mcu_specs]
    end

    %% Online Layer
    subgraph "Phase 2: Application Server (Online)"
        User((Engineer)) -->|HTTP Req| API[FastAPI Server]
        
        API -->|Search Query| Search[Faceted Search]
        API -->|Req List| Solver[Pin Mux Solver]
        API -->|App Profile| PowerCalc[Power Budget Calc]
        
        Search -->|SQL| Database[(PostgreSQL)]
        Solver -->|Fetch Pins| Database
        PowerCalc -->|Fetch Modes| Database
    end
```

---

## 🔍 2. Detailed Step-by-Step Process

### Step 1: Discovery (The "Census")
**File:** `ingestion/stm32_mcu_ingester.py`
*   **Goal**: Know what parts exist, even if we don't have data yet.
*   **Method**:
    *   Iterates through 50+ STM32 families (F0, F1, H7, etc.).
    *   Generates permutations of Model Part Numbers (MPNs) using standard naming conventions (e.g., `STM32` + `F405` + `R` + `G` + `T` + `6`).
    *   **Data Source**: Generative logic (no fake data, just valid MPN combinations).
    *   **Output**: Inserts rows into the `parts` table.

### Step 2: Acquisition (The "Crawl")
**File:** `ingestion/run_full_ingestion.py` & `ingestion/downloader.py`
*   **Goal**: Get the source of truth (datasheet).
*   **Method**:
    *   Reads `parts` table for `datasheet_url` (or constructs it).
    *   Downloads PDFs to the `/datasheets` directory.
    *   **Retry Logic**: Implements randomized sleep and User-Agent spoofing to reliably download from ST.com without getting banned.

### Step 3: Deep Extraction (The "Reading")
**File:** `ingestion/stm32_datasheet_extractor.py`
*   **Goal**: Turn PDF layout into SQL rows.
*   **Algorithm**:
    *   **Pins**: Finds tables starting with "Pin name" or "Pin number". Uses `pdfplumber` to extract text while preserving column alignment. Splits "Alternate Functions" by commas/newlines.
    *   **Specs**: Scans the "Features" section (Pages 1-5). Uses RegEx (e.g., `r"(\d+)\s*x\s*SPI"`) to find factual counts of UARTs, SPIs, etc.
    *   **Power**: Scans "Electrical Characteristics" for current consumption tables. Heuristically identifies "Run mode", "Stop mode", and extracts values in µA/mA.
*   **Output**: Updates `mcu_pin_functions` (real pins), `mcu_specs` (real counts), and `power_modes` (real µA).

### Step 4: The Solvers (The "Intelligence")

#### A. Pin Mux Solver
**File:** `solver/pin_mux_solver.py`
*   **Problem**: "I need 3x UARTs and 2x SPIs. Which pins should I use?"
*   **Algorithm (Constraint Satisfaction)**:
    1.  **Fetch**: Gets all valid pins and their Alternate Functions (AFs) for the specific part from DB.
    2.  **Graph**: Maps each requirement (UART1) to possible pins (PA9, PB6).
    3.  **Backtracking**:
        *   Tries to assign Requirement 1 to Option A.
        *   If Pin is free, PROCEED to Requirement 2.
        *   If Pin is busy, BACKTRACK and try Option B.
    4.  **Result**: A conflict-free mapping (e.g., UART1 -> PA9, SPI1 -> PA5) or "Impossible".

#### B. Power Budget Calculator
**File:** `solver/power_budget_calculator.py`
*   **Problem**: "How long will my 2000mAh battery last?"
*   **Algorithm**:
    1.  **Input**: User defines Duty Cycles (e.g., "Active 10%", "Sleep 90%").
    2.  **Lookup**: Fetches `run_current` (e.g., 15mA) and `sleep_current` (e.g., 20µA) from `power_modes` table.
    3.  **Math**:
        ```python
        avg_current = (run_ma * run_duty) + (sleep_ma * sleep_duty)
        battery_life_hours = battery_capacity_mah / avg_current
        ```
    4.  **Result**: Estimated hours/days of operation.

---

## 🛠️ 3. How to Run It (The Commands)

To populate the system with **REAL DATA** from scratch, run these commands:

### 1. Initialize Database
```bash
python scripts/setup_database.py
```
*(Creates tables. Data is empty.)*

### 2. Run Ingestion (THE BIG ONE)
This command runs the full pipeline: Discovery -> Download -> Extraction.
```bash
python ingestion/run_full_ingestion.py
```
*Note: This will verify "parts" table exists, then seek and download datasheets for all STM32 families. It takes time.*
