
import os
import psycopg2
from pathlib import Path

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

def debug():
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
        
        # Extensions first
        cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        conn.commit()

        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        sql = schema_path.read_text()
        
        print(f"Applying schema.sql...")
        cur.execute(sql)
        conn.commit()
        print("Success!")
        
    except Exception as e:
        print(f"FAILED.")
        with open("schema_error.log", "w") as f:
            f.write(str(e))
            
if __name__ == "__main__":
    debug()
