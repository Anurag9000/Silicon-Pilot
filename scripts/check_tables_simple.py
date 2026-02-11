
import os
import psycopg2

DATABASE_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

def list_tables():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables:")
        for t in tables:
            print(f"- {t[0]}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_tables()
