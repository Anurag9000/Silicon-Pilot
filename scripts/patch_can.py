
import os
import psycopg2
from pathlib import Path

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

def patch():
    print(f"Patching database with can_schema.sql...")
    try:
        parts = DB_URL.replace("postgresql://", "").split("@")
        user_pass = parts[0].split(":")
        host_port_db = parts[1].split("/")
        host_port = host_port_db[0].split(":")
        
        conn = psycopg2.connect(
            host=host_port[0],
            port=int(host_port[1]),
            user=user_pass[0],
            password=user_pass[1],
            database=host_port_db[1]
        )
        cur = conn.cursor()
        
        schema_path = Path("database/can_schema.sql")
        if not schema_path.exists():
            print("Error: can_schema.sql not found!")
            return
            
        sql = schema_path.read_text()
        
        try:
            print("Executing SQL...")
            cur.execute("DROP TABLE IF EXISTS can_specs CASCADE;")
            cur.execute(sql)
            conn.commit()
            print("✓ Success! can_specs table created/updated.")
        except Exception as e:
            print(f"❌ Failed: {e}")
            conn.rollback()
        
        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    patch()
