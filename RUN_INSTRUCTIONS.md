# Silicon-Pilot: Run Instructions

This guide provides detailed instructions on how to set up and run the Silicon-Pilot system locally or using Docker.

---

## Environment Configuration

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Anurag9000/HardwareGenius
   cd HardwareGenius
   ```

2. **Setup environment variables:**
   ```bash
   cp .env.template .env
   ```
   Edit `.env` and provide your `OPENAI_API_KEY`. The default settings for PostgreSQL, MinIO, and Redis are pre-configured for Docker.

---

## Option 1: Docker Setup (Recommended)

The easiest way to run the full stack (API, Worker, DB, S3, Redis).

1. **Start all services:**
   ```bash
   docker compose up --build -d
   ```

2. **Verify services are healthy:**
   ```bash
   docker compose ps
   ```

3. **Database initialization:**
   The database is automatically initialized, but you can manually apply the schema if needed:
   ```bash
   docker compose exec postgres psql -U hg_user -d hardwaregenius -f /docker-entrypoint-initdb.d/schema.sql
   ```

---

## Option 2: Local Development Setup

If you want to run components individually for development.

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start external dependencies:**
   You should still run DB, Redis, and MinIO via Docker:
   ```bash
   docker compose up -d postgres redis minio
   ```

3. **Run the API server:**
   ```bash
   python server.py
   ```

4. **Run the Celery worker:**
   ```bash
   python worker.py
   ```

---

## Data Ingestion Workflow

HardwareGenius starts with an empty database. You must ingest datasheets to populate it.

1. **Collect Datasheets:**
   ```bash
   python scripts/collect_stm32_datasheets.py
   ```
   Downloads ~60MB of real STM32 datasheets from st.com.

2. **Trigger Ingestion:**
   ```bash
   python scripts/ingest_datasheets.py
   ```
   Queues files for processing. Monitor logs: `docker compose logs -f worker`

---

## Accessing Interfaces

- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Console (S3)**: [http://localhost:9001](http://localhost:9001) (minioadmin / minioadmin123)
- **Database (PSQL)**:
  - Port: `5432`
  - User: `hg_user`
  - Pass: `hg_password`
  - DB: `hardwaregenius`

---

## Troubleshooting

- **Python dependencies**: Ensure you have Tesseract OCR installed on your system if running locally (`apt install tesseract-ocr`).
- **Memory issues**: PDF parsing can be memory-intensive. Ensure Docker has at least 4GB of RAM allocated.
- **Port conflicts**: Ensure ports 8000, 5432, 6379, and 9000 are available.
