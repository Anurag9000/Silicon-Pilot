
"""
Local Database Setup Script

Sets up PostgreSQL database without Docker.
Creates database, applies schema, and component tables.
Explicitly handles Extension creation to avoid transaction race conditions.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pathlib import Path

# Database connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot"
)

def setup_database():
    print("\n" + "="*60)
    print("SILICON-PILOT DATABASE SETUP (ROBUST)")
    print("="*60 + "\n")
    
    # Parse connection string
    try:
        parts = DATABASE_URL.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")
        
        user = user_pass[0]
        password = user_pass[1]
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        dbname = host_port_db[1]
    except Exception as e:
        print(f" Error parsing connection string: {e}")
        return False
    
    # Step 1: Create Database if not exists
    try:
        print(f"Connecting to postgres system db at {host}:{port}...")
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
        if not cursor.fetchone():
            print(f"Creating database '{dbname}'...")
            cursor.execute(f"CREATE DATABASE {dbname}")
        else:
            print(f"✓ Database '{dbname}' exists")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f" System DB Error: {e}")
        return False

    # Step 2: Apply Schema
    try:
        print(f"Connecting to target database '{dbname}'...")
        conn = psycopg2.connect(
            host=host, port=port, user=user, password=password, database=dbname
        )
        conn.autocommit = True # Auto commit for extensions
        cursor = conn.cursor()
        
        # A. Create Extensions explicitly first
        print("Ensuring Extensions exist...")
        try:
            cursor.execute('DROP SCHEMA public CASCADE; CREATE SCHEMA public;')
            cursor.execute('GRANT ALL ON SCHEMA public TO postgres;')
            cursor.execute('GRANT ALL ON SCHEMA public TO public;')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
            cursor.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
            print("✓ Schema reset and extensions created")
        except Exception as e:
            print(f" Schema/Extension warning: {e}")

        # B. Apply SQL Files
        root = Path(__file__).parent.parent / "database"
        files = [
            "schema.sql", 
            "component_tables.sql", 
            "errata_schema.sql", 
            "ldo_schema.sql",
            "dcdc_schema.sql",
            "pmic_schema.sql",
            "sensor_schema.sql",
            "passive_schema.sql",
            "pin_mux_schema.sql",
            "power_budget_schema.sql"
        ]
        
        for fname in files:
            fpath = root / fname
            if fpath.exists():
                print(f"Applying {fname}...")
                sql = fpath.read_text()
                try:
                    cursor.execute(sql)
                    print(f"✓ {fname} applied")
                except Exception as e:
                    print(f"\n@@@@ ERROR applying {fname} @@@@")
                    print(f"{e}")
                    print("@@@@ END ERROR @@@@\n")
                    # Don't return, try next
            else:
                print(f" Skipped {fname} (not found)")
                
        cursor.close()
        conn.close()
        print("\nSETUP COMPLETE.")
        return True
        
    except Exception as e:
        print(f" Application Error: {e}")
        return False

if __name__ == "__main__":
    setup_database()
