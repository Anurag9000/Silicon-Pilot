"""
Quick Database Setup Guide

Since PostgreSQL is not installed, here are the options:

Option 1: Install PostgreSQL locally
- Download: https://www.postgresql.org/download/windows/
- Install with default settings
- Username: postgres, Password: (set during install)
- Port: 5432

Option 2: Use Docker
- Install Docker Desktop: https://www.docker.com/products/docker-desktop
- Run: docker-compose up -d postgres

Option 3: Use SQLite (temporary, for testing only)
- Modify core/database.py to use SQLite instead
- Not recommended for production

For now, I'll create a mock database mode for testing.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print(__doc__)

# Check if PostgreSQL is available
try:
    import psycopg2
    print("\n✓ psycopg2 installed")
    
    # Try to connect
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="postgres"
        )
        print("✓ PostgreSQL is running!")
        conn.close()
        
        print("\nRun: python scripts/setup_database.py")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ PostgreSQL not running: {e}")
        print("\nPlease install PostgreSQL or Docker first.")
        
except ImportError:
    print("\n❌ psycopg2 not installed")
    print("   Install: pip install psycopg2-binary")
