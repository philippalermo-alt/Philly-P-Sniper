from database import get_db

def check_timestamp():
    print("--- DIAGNOSTIC: TIME CHECK ---")
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    try:
        cur = conn.cursor()
        
        # 1. Check App Settings (Primary Source)
        cur.execute("SELECT value FROM app_settings WHERE key='model_last_run'")
        row = cur.fetchone()
        print(f"1. app_settings['model_last_run']: {row[0] if row else 'NONE'}")

        # 2. Check Max Log Timestamp (Secondary Source)
        cur.execute("SELECT MAX(timestamp) FROM intelligence_log")
        row = cur.fetchone()
        print(f"2. intelligence_log MAX(timestamp): {row[0] if row else 'NONE'}")
        
        # 3. Check Recent Entries
        cur.execute("SELECT timestamp, outcome FROM intelligence_log ORDER BY timestamp DESC LIMIT 3")
        rows = cur.fetchall()
        print("3. Recent Logs:")
        for r in rows:
            print(f"   - {r[0]} ({r[1]})")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_timestamp()
