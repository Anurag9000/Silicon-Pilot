
import os
import psycopg2
from pathlib import Path

DATABASE_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

def init_components():
    print("Forcing component table initialization...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Read components SQL
        sql_path = Path("database/component_tables.sql")
        if not sql_path.exists():
            print(f"Error: {sql_path} not found")
            return

        sql_content = sql_path.read_text()
        # Split by semicolon to execute individually to handle errors per statement
        statements = sql_content.split(';')
        
        success_count = 0
        error_count = 0
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
                
            try:
                cursor.execute(stmt)
                success_count += 1
            except psycopg2.errors.DuplicateTable:
                print(f"  [SKIP] Table already exists")
                error_count += 1
            except psycopg2.errors.DuplicateObject:
                print(f"  [SKIP] Object already exists")
                error_count += 1
            except Exception as e:
                # Expect triggers/indexes to fail if table exists, etc.
                # But we want to ensure missing ones are created.
                if "already exists" in str(e):
                     print(f"  [SKIP] {str(e).splitlines()[0]}")
                else:
                    print(f"  [ERROR] {e}")
                error_count += 1

        print(f"\nExecuted {success_count} statements. Skipped {error_count} existing/errors.")
        print("Component tables should now exist.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    init_components()
