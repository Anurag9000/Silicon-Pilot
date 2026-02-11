
# Remaining Tasks & Missing Features

## Phase 2: Exhaustive STM32 Coverage (Refinements)
- [ ] **Errata Download Reliability**: Improve `stm32_errata_ingester.py` to handle ST.com access issues (retries, alternative URLs).
- [ ] **Advanced Parsing**: Implement "Parse ALL ordering code variants" logic (currently partial).

## Phase 3: Component Category Expansion
- [ ] **Priority Ingesters**:
    - [ ] PMICs (Power Management ICs)
    - [ ] DC-DC Converters
    - [ ] CAN Transceivers
    - [ ] Sensors
    - [ ] Passives (Resistors, Capacitors)
- [ ] **Data Sources**: Identify and implement scrapers/API clients for these non-MCU parts.

## Phase 4: BOM Cost Optimization
- [ ] **Pricing Integration**: Connect real pricing API (Octopart/DigiKey) to `PricingFetcher` (currently mock).
- [ ] **Stock Availability**: basic field exists, but real-time stock checking is missing.

## Phase 5: Design Rule Checks (DRCs)
- [ ] **DRC Rules Implementation**: `solver/design_rule_checker.py` exists (base), but specific rules are missing:
    - [ ] Power supply (VDD/VSS checks)
    - [ ] Communication (Signal integrity, termination)
    - [ ] Clock (Crystal matching)
    - [ ] Memory (Flash/RAM sufficiency)
    - [ ] Thermal constraints

## Phase 6: Reference Design Library
- [ ] **Matcher Logic**: `architecture/reference_design_matcher.py` exists (base), but advanced matching logic (similarity scoring) is minimal.

## Phase 10: ML-Based Ranking
- [ ] **ML Model**: `solver/ml_ranking.py` (LightGBM/XGBoost implementation) is missing. Current `ranking.py` uses heuristic manual weights.
- [ ] **Training Pipeline**: No script to train the ranking model on user selection data.

## Phase 12: Integration & Testing
- [ ] **Golden Suite**: `tests/golden_scenarios.json` (Data file) is missing.
- [ ] **End-to-End Stress Test**: Test with full 5,000+ SKU database (currently tested on subset).

## Production Hardening
- [ ] **Authentication**: User Accounts/Login not implemented.
- [ ] **Deployment**: HTTPS/SSL (Nginx reverse proxy) and CI/CD Pipeline (GitHub Actions) missing.