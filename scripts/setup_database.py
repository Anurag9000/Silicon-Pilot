"""
Local Database Setup Script

Sets up PostgreSQL database without Docker.
Creates database, applies schema, and component tables.
"""

import os
import sys
from pathlib import Path

# Database connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hg_user:hg_password@localhost:5432/hardwaregenius"
)

def setup_database():
    """Setup database with schema"""
    print("\n" + "="*60)
    print("HARDWAREGENIUS DATABASE SETUP")
    print("="*60 + "\n")
    
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("❌ psycopg2 not installed")
        print("   Install: pip install psycopg2-binary")
        return False
    
    # Parse connection string
    # Format: postgresql://user:pass@host:port/dbname
    parts = DATABASE_URL.replace("postgresql://", "").split("@")
    user_pass = parts[0].split(":")
    host_port_db = parts[1].split("/")
    host_port = host_port_db[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1]
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    dbname = host_port_db[1]
    
    print(f"Connecting to PostgreSQL at {host}:{port}...")
    
    # Step 1: Connect to postgres database to create our database
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (dbname,)
        )
        
        if cursor.fetchone():
            print(f"✓ Database '{dbname}' already exists")
        else:
            print(f"Creating database '{dbname}'...")
            cursor.execute(f"CREATE DATABASE {dbname}")
            print(f"✓ Database '{dbname}' created")
        
        cursor.close()
        conn.close()
    
    except psycopg2.OperationalError as e:
        print(f"❌ Cannot connect to PostgreSQL: {e}")
        print("\nMake sure PostgreSQL is running:")
        print("  Windows: Check Services for 'postgresql'")
        print("  Linux/Mac: sudo systemctl start postgresql")
        return False
    
    # Step 2: Connect to our database and apply schema
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname
        )
        cursor = conn.cursor()
        
        # Apply main schema
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        if schema_path.exists():
            print(f"\nApplying schema from {schema_path.name}...")
            schema_sql = schema_path.read_text()
            cursor.execute(schema_sql)
            conn.commit()
            print("✓ Main schema applied")
        else:
            print(f"⚠ Schema file not found: {schema_path}")
        
        # Apply component tables
        component_path = Path(__file__).parent.parent / "database" / "component_tables.sql"
        if component_path.exists():
            print(f"\nApplying component tables from {component_path.name}...")
            component_sql = component_path.read_text()
            cursor.execute(component_sql)
            conn.commit()
            print("✓ Component tables applied")
        else:
            print(f"⚠ Component tables file not found: {component_path}")
        
        # Verify tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n✓ Database ready with {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✓ DATABASE SETUP COMPLETE")
        print("="*60)
        print(f"\nConnection string: {DATABASE_URL}")
        print("\nSet environment variable:")
        print(f"  export DATABASE_URL='{DATABASE_URL}'")
        print(f"  # or on Windows:")
        print(f"  set DATABASE_URL={DATABASE_URL}")
        
        return True
    
    except Exception as e:
        print(f"❌ Error applying schema: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
