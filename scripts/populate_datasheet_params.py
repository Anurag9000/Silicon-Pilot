#!/usr/bin/env python3
"""
populate_datasheet_params.py
=============================

Reads every PDF listed in data/stm32_datasheets/manifest.json,
runs DeepDatasheetExtractor on each, and inserts all extracted
parameters into the datasheet_parameters table.

Works against the mock SQLite DB (default) or real Postgres:
  python scripts/populate_datasheet_params.py          # mock SQLite
  REAL_DB=true python scripts/populate_datasheet_params.py  # Postgres
"""

import sys
import os
import uuid
import json
import sqlite3
import logging
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.deep_datasheet_extractor import DeepDatasheetExtractor

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MANIFEST_PATH = Path("data/stm32_datasheets/manifest.json")
MOCK_DB_PATH  = Path("data/siliconpilot_mock.db")


# ──────────────────────────────────────────────────────────────────────────────
# SQLite (mock) driver
# ──────────────────────────────────────────────────────────────────────────────

def find_part_id_sqlite(conn: sqlite3.Connection, name: str) -> str | None:
    """Fuzzy search by MPN prefix (e.g. 'STM32H743' matches 'STM32H743VIT6')."""
    cur = conn.execute(
        "SELECT id FROM parts WHERE mpn LIKE ? LIMIT 1",
        (f"{name}%",)
    )
    row = cur.fetchone()
    return row[0] if row else None


def insert_params_sqlite(conn: sqlite3.Connection, part_id: str, params: list) -> int:
    cur = conn.cursor()
    inserted = 0
    for p in params:
        try:
            cur.execute("""
                INSERT OR REPLACE INTO datasheet_parameters (
                    id, part_id, section, parameter,
                    min_value, typ_value, max_value, unit, conditions,
                    source_page, raw_text, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                part_id,
                p.get("section", "unknown"),
                p.get("parameter", "")[:255],
                p.get("min_value", "-"),
                p.get("typ_value", "-"),
                p.get("max_value", "-"),
                p.get("unit", ""),
                p.get("conditions", ""),
                p.get("source_page"),
                (p.get("raw_text", "") or "")[:500],
                p.get("confidence", 1.0),
            ))
            inserted += 1
        except Exception as e:
            logger.debug(f"Skip row: {e}")
    conn.commit()
    return inserted


def run_sqlite(manifest: list) -> None:
    db_path = MOCK_DB_PATH
    if not db_path.exists():
        logger.error(f"Mock DB not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))

    # Ensure the table exists (in case a fresh DB was just created)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS datasheet_parameters (
            id TEXT PRIMARY KEY,
            part_id TEXT NOT NULL,
            section TEXT NOT NULL,
            parameter TEXT NOT NULL,
            min_value TEXT,
            typ_value TEXT,
            max_value TEXT,
            unit TEXT,
            conditions TEXT,
            source_page INTEGER,
            raw_text TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    total_inserted = 0
    matched = 0

    for entry in manifest:
        name = entry["name"]
        local_path = Path(entry["local_path"])

        if not local_path.exists():
            logger.warning(f"PDF not found: {local_path}")
            continue

        part_id = find_part_id_sqlite(conn, name)
        if not part_id:
            logger.info(f"No part row found for '{name}', skipping")
            continue

        matched += 1
        logger.info(f"Extracting {name} (part_id={part_id[:8]}…)")

        extractor = DeepDatasheetExtractor(str(local_path), name)
        params = extractor.extract_all()

        inserted = insert_params_sqlite(conn, part_id, params)
        total_inserted += inserted
        logger.info(f"  → {len(params)} params extracted, {inserted} inserted")

    conn.close()
    logger.info(f"\nDone. Matched {matched} parts, inserted {total_inserted} rows total.")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    if not MANIFEST_PATH.exists():
        logger.error(f"Manifest not found: {MANIFEST_PATH}")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        data = json.load(f)
    manifest = data.get("datasheets", [])

    logger.info(f"Manifest has {len(manifest)} datasheets")
    run_sqlite(manifest)


if __name__ == "__main__":
    main()
