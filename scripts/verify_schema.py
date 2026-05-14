
import os
import psycopg2
from pathlib import Path

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/siliconpilot")

def verify():
    print(f"Verifying schema.sql execution on {DB_URL}...")
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
        
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        sql_content = schema_path.read_text()
        
        # Naive split by ';' - might break on stored procs or strings containing ; but 
        # schema.sql is simple enough.
        statements = sql_content.split(';')
        
        for i, stmt in enumerate(statements):
            stmt = stmt.strip()
            if not stmt:
                continue
                
            print(f"--- Executing Statement {i+1} ---")
            snippet = stmt[:50].replace('\n', ' ')
            print(f"SQL: {snippet}...")
            
            try:
                cur.execute(stmt)
                print("✓ Success")
            except Exception as e:
                print(f" FAILED: {e}")
                print(f"Full Statement:\n{stmt}")
                conn.rollback() # Rollback transaction to continue? 
                # Actually if we want to proceed we need valid state.
                # But for debugging, knowing WHICH fails is enough.
                break
                
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    verify()
