
import os
import psycopg2
from pathlib import Path

# Database connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot"
)

def apply_errata():
    print(f"Applying Errata Schema to {DATABASE_URL}...")
    
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
        print(f"Error parsing URL: {e}")
        return

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read schema
        errata_path = Path(__file__).parent.parent / "database" / "errata_schema.sql"
        if not errata_path.exists():
            print(f"Error: {errata_path} not found")
            return

        sql = errata_path.read_text()
        print(f"Executing SQL from {errata_path.name}...")
        cursor.execute(sql)
        print("✓ Applied successfully.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    apply_errata()
