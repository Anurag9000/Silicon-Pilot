# Silicon-Pilot Database

## Quick Setup for Demo

### Prerequisites
- PostgreSQL 14+
- Python 3.10+
- Ollama with `qwen2.5:1.5b` model

### 1. Create the database

```bash
createdb hardwaregenius
# OR: psql -c "CREATE DATABASE hardwaregenius;"
```

### 2. Load schema + data

```bash
# Load schema first
psql hardwaregenius < database/dumps/schema.sql

# Load 461 real STM32 board data + 5071 datasheet parameters
psql hardwaregenius < database/dumps/hardware_data.sql
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set DATABASE_URL to your PostgreSQL connection string
# e.g.: DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/hardwaregenius
```

### 4. Start the server

```bash
pip install -r requirements.txt
PYTHONPATH=. python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### 5. Open the UI

Visit http://localhost:8000

## Database Contents

| Table | Rows | Description |
|-------|------|-------------|
| `parts` | 461 | Real STM32 MCU boards |
| `mcu_specs` | 461 | Detailed MCU specs (flash, RAM, peripherals, etc.) |
| `datasheet_parameters` | 5071 | PDF-extracted electrical parameters |
| Other tables | — | Schema for templates, conflicts, evidence, etc. |

## Families Covered

All STM32 families: STM32C0, STM32F0, STM32F1, STM32F2, STM32F3, STM32F4, STM32F7, STM32G0, STM32G4, STM32H5, STM32H7, STM32L0, STM32L1, STM32L4, STM32L5, STM32U0, STM32U5, STM32WB, STM32WL

## Notes

- Dump was created with `pg_dump --no-owner --no-privileges`
- No credentials are stored in the dumps
- The `.env` file is gitignored — configure it manually
