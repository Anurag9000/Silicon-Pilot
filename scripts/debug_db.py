
import os
import psycopg2
import sys

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius")

def debug_db():
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
        
        # Check Version
        cur.execute("SELECT version();")
        print(f"Version: {cur.fetchone()[0]}")
        
        # Check Extensions
        cur.execute("SELECT * FROM pg_extension;")
        print("\nExtensions:")
        for row in cur.fetchall():
            print(row)
            
        # Test UUID
        print("\nTesting uuid_generate_v4()...")
        try:
            cur.execute("SELECT uuid_generate_v4();")
            print(f"Success: {cur.fetchone()[0]}")
        except Exception as e:
            print(f"Failed: {e}")
            conn.rollback()
            
        print("\nTesting gen_random_uuid()...")
        try:
            cur.execute("SELECT gen_random_uuid();")
            print(f"Success: {cur.fetchone()[0]}")
        except Exception as e:
            print(f"Failed: {e}")
            conn.rollback()

        # List Tables
        print("\nTables:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        for row in cur.fetchall():
            print(f" - {row[0]}")
            
        print("\n--- Part Counts ---")
        cur.execute("SELECT COUNT(*) FROM parts WHERE mpn LIKE 'STM32%'")
        print(f"STM32 Parts: {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM parts WHERE mpn NOT LIKE 'STM32%'")
        print(f"Other Parts: {cur.fetchone()[0]}")
        
        cur.execute("SELECT COUNT(*) FROM dcdc_specs")
        print(f"DC-DC Specs: {cur.fetchone()[0]}")


        conn.close()
        
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    debug_db()
