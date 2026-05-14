import os
import shutil
import subprocess
import time
import sys
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATASHEETS_DIR = DATA_DIR / "stm32_datasheets"
SNIPPETS_DIR = DATA_DIR / "snippets"
DB_NAME = "siliconpilot"

# Postgres commands
PG_ENV = os.environ.copy()
PG_ENV["PGPASSWORD"] = "1Anurag2Basistha"
PSQL = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"
USER = "postgres"
HOST = "localhost"

def run_command(cmd, shell=False, env=None):
    print(f"\n[EXEC] {cmd}")
    subprocess.run(cmd, check=True, shell=shell, env=env)

def main():
    print("!!! INITIATING FULL SYSTEM RESET !!!")
    
    # 1. Kill potential lingering processes (Best effort)
    print("\n--- Step 1: Cleaning Processes ---")
    # Skipped self-termination. Expected external cleanup.
    # os.system("taskkill /F /IM python.exe /T 2>nul") 
    time.sleep(2)

    # 2. Recreate Database
    print("\n--- Step 2: Recreating Database ---")
    terminate_sql = f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{DB_NAME}';"
    try:
        # Kill connections
        subprocess.run([PSQL, "-U", USER, "-h", HOST, "-d", "postgres", "-c", terminate_sql], env=PG_ENV, check=False)
        # Drop DB
        subprocess.run([PSQL, "-U", USER, "-h", HOST, "-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {DB_NAME};"], env=PG_ENV, check=True)
        # Create DB
        subprocess.run([PSQL, "-U", USER, "-h", HOST, "-d", "postgres", "-c", f"CREATE DATABASE {DB_NAME};"], env=PG_ENV, check=True)
        # Apply Schema
        subprocess.run([PSQL, "-U", USER, "-h", HOST, "-d", DB_NAME, "-f", str(BASE_DIR / "database/schema.sql")], env=PG_ENV, check=True)
        subprocess.run([PSQL, "-U", USER, "-h", HOST, "-d", DB_NAME, "-f", str(BASE_DIR / "database/component_tables.sql")], env=PG_ENV, check=True)
        print("✓ Database refreshed.")
    except Exception as e:
        print(f" Database error: {e}")
        return

    # 3. Purge Data
    print("\n--- Step 3: Purging Data Directories ---")
    if DATASHEETS_DIR.exists():
        print(f"Deleting {DATASHEETS_DIR}")
        shutil.rmtree(DATASHEETS_DIR)
    if SNIPPETS_DIR.exists():
        print(f"Deleting {SNIPPETS_DIR}")
        shutil.rmtree(SNIPPETS_DIR)
    
    DATASHEETS_DIR.mkdir(parents=True, exist_ok=True)
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    print("✓ Data purged.")

    # 4. Run Downloader
    print("\n--- Step 4: Exhaustive Download (This may take time) ---")
    try:
        subprocess.run([sys.executable, str(BASE_DIR / "ingestion/stm32_downloader.py")], check=True)
    except Exception as e:
        print(f" Download failed: {e}")
        return

    # 5. Run Ingestion
    print("\n--- Step 5: Data Ingestion ---")
    try:
        subprocess.run([sys.executable, str(BASE_DIR / "ingestion/run_stm32_ingestion.py")], check=True)
    except Exception as e:
        print(f" Ingestion failed: {e}")
        return

    print("\n--- RESET COMPLETE ---")
    print("Starting Server...")
    subprocess.run([sys.executable, str(BASE_DIR / "server.py")])

if __name__ == "__main__":
    main()
