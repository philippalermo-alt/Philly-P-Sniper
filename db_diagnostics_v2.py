
import pandas as pd
from database import get_db

def run_diagnostics():
    conn = get_db()
    
    print("--- 1. Checking 'model_last_run' ---")
    try:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM app_settings WHERE key = 'model_last_run'")
        print(cur.fetchall())
    except Exception as e:
        print(f"Error checking settings: {e}")

    print("\n--- 2. Checking `player_stats` for bad team_id ---")
    try:
        # Check non-numeric
        sql = "SELECT team_id, count(*) FROM player_stats GROUP BY team_id"
        df = pd.read_sql(sql, conn)
        print(df.head(20))
        
        # Check specific 'h' case if possible?
        # SQL will likely throw error if column is Integer but data is 'h' (unless it's VARCHAR)
        # Check schema first?
        cur.execute("SELECT data_type FROM information_schema.columns WHERE table_name='player_stats' AND column_name='team_id'")
        dtype = cur.fetchall()
        print(f"Schema for team_id: {dtype}")

    except Exception as e:
        print(f"Error checking player_stats: {e}")

    print("\n--- 3. Checking `intelligence_log` for 'oNone' ---")
    try:
        sql = "SELECT id, event_id, selection, market, timestamp FROM intelligence_log WHERE selection LIKE '%oNone%' OR market LIKE '%oNone%' ORDER BY timestamp DESC LIMIT 10"
        df_log = pd.read_sql(sql, conn)
        print(df_log)
    except Exception as e:
        print(f"Error checking log: {e}")

    conn.close()

if __name__ == "__main__":
    run_diagnostics()
