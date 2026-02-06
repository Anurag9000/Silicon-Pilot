# HardwareGenius: Test Data Setup Guide

This guide explains how to prepare and reset the environment for thorough system testing.

---

## 1. Database Reset

To clear the database and start fresh for a new test run:
```bash
# Using Docker
docker compose exec postgres psql -U hg_user -d hardwaregenius -c "TRUNCATE parts, mcu_specs, evidence, documents RESTART IDENTITY CASCADE;"
```

---

## 2. Evidence Store (MinIO) Reset

To clear old snippets and PDFs:
```bash
# Delete all objects in buckets (requires mc or manual deletion in UI)
# Navigate to http://localhost:9001 and delete 'documents' and 'evidence' bucket contents.
```

---

## 3. Preparing the Golden Test State

The **Golden Test Suite** requires specific parts to be in the database to pass.

1. **Standard Ingestion**:
   ```bash
   python scripts/collect_stm32_datasheets.py
   python scripts/ingest_datasheets.py
   ```

2. **Manual Seeding (for specific test cases)**:
   If you need to test a specific part without a datasheet, use a seed script (not provided for MVP, use SQL directly):
   ```sql
   INSERT INTO parts (mpn, manufacturer, family) VALUES ('SEED-PART-01', 'TestMfg', 'TestFamily');
   ```

---

## 4. Running Regression Tests

After any logic change, run the regression suite:
1. `pytest tests/test_hard_filter.py`
2. `pytest tests/test_ranking.py`
3. `pytest tests/test_integration.py`

---

## 5. Performance Benchmarking Data

To test performance at scale:
1. Increase the limit in `scripts/exhaustive_crawler.py`.
2. Download 500+ datasheets.
3. Run ingestion (caution: this may take several hours).
4. Measure `/recommend` response time using `timeit` or similar tools.
