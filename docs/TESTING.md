# Silicon-Pilot: Test Guide

Silicon-Pilot includes a comprehensive test suite covering deterministic filtering, ranking explainability, and ingestion accuracy.

---

##  Quick Verification

Run the quick test to verify the ingestion pipeline and solver logic without a database:
```bash
python quick_test.py
```

---

##  Automated Test Categories

### 1. Hard Filter Tests
Verifies that the solver never violates hard constraints and remains 100% deterministic over 100+ runs.
```bash
pytest tests/test_hard_filter.py -v
```

### 2. Ranking Tests
Verifies that the multi-criteria scoring correctly ranks parts based on optimization goals (Cost, Power, Performance).
```bash
pytest tests/test_ranking.py -v
```

### 3. Golden Test Suite
A collection of 50+ real-world requirement scenarios derived from engineering projects. This ensures that expert-recommended parts always appear in the top results.
```bash
pytest tests/test_golden_scenarios.py -v
```

### 4. Integration Tests
Tests the full pipeline from natural language input to final recommendation with evidence.
```bash
pytest tests/test_integration.py -v
```

---

##  Running All Tests

Inside the Docker container (ensures correct environment):
```bash
docker compose exec backend pytest tests/ -v
```

Locally:
```bash
pytest .
```

---

##  Evaluation Metrics

When running tests, pay attention to these key indicators:
- **Hallucination Rate**: (Must be 0.0) Checked by verifying every recommended spec field exists in the Evidence table.
- **Determinism**: Checked by running the same query multiple times and comparing hashes of the response.
- **Evidence Coverage**: The percentage of recommended parts that include a direct link to a datasheet snippet.

---

##  Writing New Tests

New golden tests should be added to `tests/test_golden_scenarios.py`. Use the following pattern:

```python
{
    "id": "USR-001",
    "description": "User specific scenario",
    "query": "Need Cortex-M7 with high clock speed",
    "constraints": {
        "core": "ARM Cortex-M7",
        "max_mhz": {"min": 400}
    },
    "expected_mpns": ["STM32H743ZI"],
    "optimization": OptimizationGoal.PERFORMANCE
}
```
