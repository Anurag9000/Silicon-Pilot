# Silicon-Pilot - Data Ingestion Guide

## Overview

This guide walks through collecting real STM32 datasheets and ingesting them into the system.

---

## Step 1: Start Services

```powershell
# Copy environment template
Copy-Item .env.template .env

# Edit .env and add your OPENAI_API_KEY
notepad .env

# Start all services
docker-compose up --build -d

# Verify services are running
docker-compose ps
```

**Expected services:**
- `postgres` - Database
- `minio` - S3 storage
- `redis` - Task queue
- `backend` - FastAPI server
- `worker` - Celery worker

---

## Step 2: Initialize Database

```powershell
# Apply schema
docker-compose exec postgres psql -U hg_user -d siliconpilot -f /docker-entrypoint-initdb.d/schema.sql

# Verify tables created
docker-compose exec postgres psql -U hg_user -d siliconpilot -c "\dt"
```

---

## Step 3: Collect STM32 Datasheets

```powershell
# Install dependencies (if not in Docker)
pip install requests beautifulsoup4

# Run collector
python scripts/collect_stm32_datasheets.py
```

**This will download:**
- 15+ STM32 family datasheets (F0-F7, G0/G4, H7, L0-L5, U5, WB, WL)
- Save to `data/stm32_datasheets/`
- Create `manifest.json` with URLs and metadata

**Example output:**
```
 Downloaded 15 STM32 datasheets
 Saved to: data\stm32_datasheets
 Manifest: data\stm32_datasheets\manifest.json
```

---

## Step 4: Ingest Datasheets

```powershell
# Queue ingestion tasks
python scripts/ingest_datasheets.py --manifest data/stm32_datasheets/manifest.json
```

**This will:**
- Read manifest.json
- Queue each datasheet for processing
- Save task IDs to `ingestion_tasks.json`

---

## Step 5: Monitor Ingestion

```powershell
# Watch Celery worker logs
docker-compose logs -f worker

# Check database for ingested parts
docker-compose exec postgres psql -U hg_user -d siliconpilot -c "SELECT COUNT(*) FROM parts;"

# Check evidence records
docker-compose exec postgres psql -U hg_user -d siliconpilot -c "SELECT COUNT(*) FROM evidence;"
```

---

## Step 6: Test Recommendations

```powershell
# Access API docs
start http://localhost:8000/docs

# Test parse requirements endpoint
curl -X POST http://localhost:8000/spec/from_text `
  -H "Content-Type: application/json" `
  -d '{"text": "Need Cortex-M4, at least 512KB flash, 2 CAN, QFP package"}'

# Test recommendation endpoint
# (Use spec_id from previous response)
curl -X POST http://localhost:8000/recommend `
  -H "Content-Type: application/json" `
  -d '{"spec_id": "YOUR_SPEC_ID", "max_results": 10}'
```

---

## Troubleshooting

### Worker not processing tasks
```powershell
# Restart worker
docker-compose restart worker

# Check Redis connection
docker-compose exec redis redis-cli ping
```

### Database connection issues
```powershell
# Check PostgreSQL logs
docker-compose logs postgres

# Verify connection
docker-compose exec postgres psql -U hg_user -d siliconpilot -c "SELECT 1;"
```

### MinIO storage issues
```powershell
# Access MinIO console
start http://localhost:9001

# Login: minioadmin / minioadmin123
# Check buckets: documents, evidence
```

---

## Ingestion Pipeline Details

Each datasheet goes through:

1. **Fetch** - Download PDF, compute SHA-256, store in MinIO
2. **Parse** - Extract text, tables, images with PyMuPDF/Camelot/Tesseract
3. **Extract** - Regex + table extraction for specs (flash, RAM, CAN, etc.)
4. **Normalize** - Unit conversion, synonym mapping, package normalization
5. **Validate** - Type/range checks, cross-source conflict detection
6. **Publish** - Transactional insert to PostgreSQL with evidence

---

## Expected Results

After ingestion, you should have:

- **Parts table**: 15+ STM32 families
- **MCU specs**: Flash, RAM, peripherals, package, temp range
- **Evidence**: Source URLs, page numbers, bboxes, confidence scores
- **Documents**: Cached PDFs with SHA-256 hashes

---

## Next Steps

1. **Run tests**: `docker-compose exec backend pytest tests/ -v`
2. **Try recommendations**: Use API docs at http://localhost:8000/docs
3. **Review conflicts**: Check `GET /admin/conflicts` endpoint
4. **Add more vendors**: Extend collector for ESP32, nRF, RP2040

---

## Production Deployment

For production:

1. Use real S3 (not MinIO)
2. Set up PostgreSQL with replication
3. Add authentication to API
4. Configure rate limiting
5. Set up monitoring (Prometheus/Grafana)
6. Enable HTTPS
