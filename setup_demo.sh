#!/usr/bin/env bash
# Silicon-Pilot Demo Setup Script
# Run this after git clone to get the app working in minutes.

set -e
BLUE='\033[0;34m'; GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${BLUE}=== Silicon-Pilot Demo Setup ===${NC}"

# 1. Check prerequisites
command -v psql >/dev/null || { echo -e "${RED} psql not found. Install PostgreSQL.${NC}"; exit 1; }
command -v python3 >/dev/null || { echo -e "${RED} python3 not found.${NC}"; exit 1; }

# 2. Get DB credentials
read -p "PostgreSQL user [postgres]: " PG_USER
PG_USER=${PG_USER:-postgres}
read -s -p "PostgreSQL password: " PG_PASS
echo ""
read -p "PostgreSQL host [localhost]: " PG_HOST
PG_HOST=${PG_HOST:-localhost}
read -p "Database name [siliconpilot]: " PG_DB
PG_DB=${PG_DB:-siliconpilot}

DB_URL="postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:5432/${PG_DB}"

# 3. Create database if needed
echo -e "${BLUE}Creating database '${PG_DB}'...${NC}"
psql "postgresql://${PG_USER}:${PG_PASS}@${PG_HOST}:5432/postgres" -c "CREATE DATABASE ${PG_DB};" 2>/dev/null || true

# 4. Load schema
echo -e "${BLUE}Loading schema...${NC}"
psql "$DB_URL" < database/dumps/schema.sql
echo -e "${GREEN} Schema loaded${NC}"

# 5. Load data
echo -e "${BLUE}Loading 461 real STM32 boards + 5071 datasheet parameters...${NC}"
psql "$DB_URL" < database/dumps/hardware_data.sql
echo -e "${GREEN} Data loaded${NC}"

# 6. Create .env
cat > .env << EOF
DATABASE_URL=${DB_URL}
REAL_DATABASE_URL=${DB_URL}
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:1.5b
OLLAMA_HOST=http://localhost:11434
LOG_LEVEL=INFO
EOF
echo -e "${GREEN} .env created${NC}"

# 7. Install dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN} Dependencies installed${NC}"

echo ""
echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo -e "Start the server:  ${BLUE}PYTHONPATH=. python3 -m uvicorn server:app --host 0.0.0.0 --port 8000${NC}"
echo -e "Open the UI:       ${BLUE}http://localhost:8000${NC}"
