"""
Complete Database Initialization and Population Script

This script:
1. Drops and recreates the database (fresh start)
2. Applies all schemas
3. Populates STM32 MCU data (1000+ variants)
4. Populates component data (PMIC, DC-DC, LDO)
5. Populates firmware stacks
6. Populates reference designs

Run this for a complete fresh database with all data.
"""

import subprocess
import sys
import os
from pathlib import Path

# Database credentials
DB_NAME = "siliconpilot"
DB_USER = "postgres"
DB_PASSWORD = "1Anurag2Basistha"
DB_HOST = "localhost"
DB_PORT = "5432"

import shutil

PSQL_PATH = shutil.which("psql") or r"C:\Program Files\PostgreSQL\17\bin\psql.exe"

def run_psql(command, db=DB_NAME):
    """Run a psql command"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    cmd = [
        PSQL_PATH,
        "-U", DB_USER,
        "-h", DB_HOST,
        "-d", db,
        "-c", command
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def run_psql_file(filepath, db=DB_NAME):
    """Run a SQL file"""
    env = os.environ.copy()
    env["PGPASSWORD"] = DB_PASSWORD
    
    cmd = [
        PSQL_PATH,
        "-U", DB_USER,
        "-h", DB_HOST,
        "-d", db,
        "-f", filepath
    ]
    
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def run_python_script(script_path):
    """Run a Python script"""
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True, env=os.environ)
    return result.returncode == 0, result.stdout, result.stderr

def main():
    # Set DATABASE_URL for child processes
    os.environ["DATABASE_URL"] = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    print("="*70)
    print(" "*15 + "SILICON-PILOT DATABASE INITIALIZATION")
    print("="*70 + "\n")
    
    # Step 1: Drop and recreate database
    print("[1/8] Dropping and recreating database...")
    
    # Kill existing connections
    kill_cmd = "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'siliconpilot' AND pid <> pg_backend_pid();"
    run_psql(kill_cmd, db="postgres")
    
    success, stdout, stderr = run_psql(f"DROP DATABASE IF EXISTS {DB_NAME};", db="postgres")
    if not success:
        print(f"   Warning: {stderr}")
    
    success, stdout, stderr = run_psql(f"CREATE DATABASE {DB_NAME};", db="postgres")
    if success:
        print("  ✓ Database created\n")
    else:
        print(f"  ✗ Failed: {stderr}\n")
        return
    
    # Step 2: Apply core schema
    print("[2/8] Applying core schema...")
    success, stdout, stderr = run_psql_file("database/schema.sql")
    if success:
        print("  ✓ Core schema applied\n")
    else:
        print(f"  ✗ Failed: {stderr}\n")
        # Continue anyway - some tables might exist
    
    # Step 3: Apply component tables
    print("[3/8] Applying component tables...")
    success, stdout, stderr = run_psql_file("database/component_tables.sql")
    if success:
        print("  ✓ Component tables applied\n")
    else:
        print(f"   Warning: {stderr}\n")
    
    # Step 4: Apply additional schemas
    print("[4/8] Applying additional schemas...")
    schemas = [
        "database/errata_schema.sql",
        "database/reference_design_schema.sql",
        "database/pin_mux_schema.sql",
        "database/power_budget_schema.sql",
        "database/firmware_stack_schema.sql",
        "database/ml_ranking_schema.sql"
    ]
    
    for schema in schemas:
        if Path(schema).exists():
            success, stdout, stderr = run_psql_file(schema)
            schema_name = Path(schema).stem
            if success:
                print(f"  ✓ {schema_name}")
            else:
                print(f"   {schema_name}: {stderr[:50]}")
    print()
    
    # Step 5: Populate STM32 MCUs
    print("[5/8] Populating STM32 MCU data...")
    success, stdout, stderr = run_python_script("ingestion/stm32_mcu_ingester.py")
    if success:
        print(stdout)
    else:
        print(f"  ✗ Failed: {stderr[:200]}\n")
    
    # Step 6: Populate components
    print("[6/8] Populating component data...")
    success, stdout, stderr = run_python_script("ingestion/run_component_ingestion.py")
    if success:
        print(stdout)
    else:
        print(f"   Warning: {stderr[:200]}\n")
    
    # Step 7: Populate firmware stacks
    print("[7/8] Populating firmware stacks...")
    success, stdout, stderr = run_python_script("scripts/populate_firmware_stacks.py")
    if success:
        print(stdout)
    else:
        print(f"   Warning: {stderr[:200]}\n")
    
    # Step 8: Populate reference designs
    print("[8/8] Populating reference designs...")
    success, stdout, stderr = run_python_script("scripts/populate_reference_designs.py")
    if success:
        print(stdout)
    else:
        print(f"   Warning: {stderr[:200]}\n")
    
    # Final verification
    print("="*70)
    print(" "*20 + "VERIFICATION")
    print("="*70 + "\n")
    
    queries = [
        ("Total Parts", "SELECT COUNT(*) FROM parts;"),
        ("STM32 MCUs", "SELECT COUNT(*) FROM mcu_specs;"),
        ("PMICs", "SELECT COUNT(*) FROM pmic_specs;"),
        ("DC-DC Converters", "SELECT COUNT(*) FROM dcdc_specs;"),
        ("LDOs", "SELECT COUNT(*) FROM ldo_specs;"),
        ("Firmware Stacks", "SELECT COUNT(*) FROM firmware_stacks;"),
        ("Reference Designs", "SELECT COUNT(*) FROM reference_designs;"),
    ]
    
    for name, query in queries:
        success, stdout, stderr = run_psql(query)
        if success:
            count = stdout.strip().split('\n')[2].strip()
            print(f"  {name}: {count}")
        else:
            print(f"  {name}: Error")
    
    print("\n" + "="*70)
    print("✓ Database initialization complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
