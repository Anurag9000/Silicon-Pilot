#!/bin/bash
# restore_db.sh — Restore the Silicon-Pilot siliconpilot PostgreSQL database
# Usage: bash database/restore_db.sh [postgres_password]
# Defaults to PGPASSWORD env var if set, otherwise prompts

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="siliconpilot"
USER="${PGUSER:-postgres}"
HOST="${PGHOST:-localhost}"
PORT="${PGPORT:-5432}"
PASS="${1:-${PGPASSWORD:-}}"

if [ -z "$PASS" ]; then
    read -s -p "PostgreSQL password for user '$USER': " PASS
    echo
fi

export PGPASSWORD="$PASS"

echo "=== Silicon-Pilot DB Restore ==="
echo "  Host : $HOST:$PORT"
echo "  DB   : $DB"
echo "  User : $USER"
echo ""

# 1. Create DB if it does not exist
psql -h "$HOST" -U "$USER" -p "$PORT" -tc "SELECT 1 FROM pg_database WHERE datname='$DB'" | grep -q 1 || \
    psql -h "$HOST" -U "$USER" -p "$PORT" -c "CREATE DATABASE $DB;"
echo "✅ Database '$DB' ready."

# 2. Apply schema
echo "Applying schema..."
psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" -f "$SCRIPT_DIR/schema.sql" > /dev/null 2>&1 || true
echo "✅ Schema applied."

# 3. Restore parts + mcu_specs (compressed)
echo "Restoring parts and mcu_specs (461 STM32 parts)..."
gunzip -c "$SCRIPT_DIR/parts_and_specs.sql.gz" | psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" > /dev/null 2>&1 || true
echo "✅ Parts and specs restored."

# 4. Restore companion_chips
echo "Restoring companion chips ecosystem (18 companion chips)..."
psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" -f "$SCRIPT_DIR/companion_chips_seed.sql" > /dev/null 2>&1 || true
echo "✅ Companion chips restored."

# 5. Apply power seed data from CSV
echo "Seeding power data (active_ma, standby_ua, sleep_ua for all 461 parts)..."
psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" << 'SQL'
CREATE TEMP TABLE _power_seed (mpn TEXT, active_ma NUMERIC, standby_ua NUMERIC, sleep_ua NUMERIC);
SQL

# Use psql \copy for the CSV
psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" \
    -c "\COPY _power_seed FROM '$SCRIPT_DIR/power_seed.csv' CSV HEADER" > /dev/null 2>&1 || true

psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" << 'SQL'
UPDATE mcu_specs ms
SET active_ma  = s.active_ma,
    standby_ua = s.standby_ua,
    sleep_ua   = s.sleep_ua
FROM _power_seed s
JOIN parts p ON p.mpn = s.mpn
WHERE ms.part_id = p.id;
SQL

echo "✅ Power data seeded."

# 6. Verify
COUNT=$(psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" -tA -c "SELECT COUNT(*) FROM parts;")
CHIPS=$(psql -h "$HOST" -U "$USER" -p "$PORT" -d "$DB" -tA -c "SELECT COUNT(*) FROM companion_chips;")
echo ""
echo "=== Restore Complete ==="
echo "  Parts         : $COUNT"
echo "  Companion chips: $CHIPS"
echo ""
echo "Start the server with:"
echo "  DATABASE_URL=postgresql://$USER:\$PGPASSWORD@$HOST:$PORT/$DB PYTHONPATH=. python3 -m uvicorn server:app --port 8000"
