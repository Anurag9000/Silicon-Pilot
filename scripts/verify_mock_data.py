import sqlite3

def verify_data():
    try:
        conn = sqlite3.connect("data/siliconpilot_mock.db")
        cursor = conn.cursor()
        
        tables = ['parts', 'mcu_specs']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"Table {table}: {count} rows")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_data()
