
import psycopg2
import sys

DATABASE_URL = "postgresql://postgres:1Anurag2Basistha@localhost:5432/hardwaregenius"

def check_pmic_table():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT to_regclass('public.pmic_specs');")
        result = cursor.fetchone()[0]
        if result == 'pmic_specs':
            print("FOUND: pmic_specs exists")
        else:
            print("MISSING: pmic_specs does NOT exist")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pmic_table()
