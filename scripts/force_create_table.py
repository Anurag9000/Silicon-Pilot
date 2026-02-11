
import os
import psycopg2

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

def force_param():
    print(f"Connecting to {DB_URL}...")
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
        
        print("Checking if mcu_specs exists...")
        cur.execute("SELECT to_regclass('public.mcu_specs');")
        res = cur.fetchone()[0]
        print(f"Exists? {res}")
        
        if not res:
            print("Creating mcu_specs manually...")
            sql = """
            CREATE TABLE mcu_specs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                part_id UUID NOT NULL UNIQUE REFERENCES parts(id) ON DELETE CASCADE,
                core VARCHAR(100),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
            try:
                cur.execute(sql)
                conn.commit()
                print("Created successfully!")
            except Exception as e:
                print(f"Creation Failed: {e}")
                conn.rollback()
        
        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    force_param()
