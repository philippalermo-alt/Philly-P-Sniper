import os
import pandas as pd
import sys
from db.connection import get_db

print("--- REMOTE DB DIAGNOSTIC ---")
print(f"DEBUG: DB_HOST={os.getenv('DB_HOST')}, DB_NAME={os.getenv('DB_NAME')}")

try:
    conn = get_db()
    if not conn:
        print("❌ Failed to connect to DB")
        sys.exit(1)
        
    cur = conn.cursor()
    
    # Check Table Existence
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name   = 'nba_historical_games')")
    exists = cur.fetchone()[0]
    print(f"Table 'nba_historical_games' exists: {exists}")
    
    if not exists:
        print("CRITICAL: Table missing!")
        sys.exit(0)

    # 1. Count
    cur.execute("SELECT COUNT(*) FROM nba_historical_games")
    count = cur.fetchone()[0]
    print(f"Total Rows in nba_historical_games: {count}")
    
    if count > 0:
        cur.execute("SELECT MIN(game_date), MAX(game_date) FROM nba_historical_games")
        rng = cur.fetchone()
        print(f"Date Range: {rng[0]} to {rng[1]}")
    
    # 2. BOS Query (Abbr)
    # The code maps 'Boston Celtics' to 'BOS'. 
    # Let's check for 'BOS' or 'Boston Celtics' to be sure what is in DB.
    
    print("Checking for 'BOS' (Abbr)...")
    q_hist = """
        SELECT * FROM nba_historical_games 
        WHERE (home_team_name = 'BOS' OR away_team_name = 'BOS')
        ORDER BY game_date DESC LIMIT 5
    """
    # Use raw cursor first to avoid pandas warning noise
    cur.execute(q_hist)
    rows = cur.fetchall()
    print(f"BOS rows found: {len(rows)}")
    for r in rows:
        print(f" - {r}")
        
    # Check full name just in case
    print("Checking for 'Boston Celtics' (Full)...")
    cur.execute("SELECT count(*) FROM nba_historical_games WHERE home_team_name = 'Boston Celtics'")
    print(f"Rows with full name: {cur.fetchone()[0]}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        conn.close()
    except:
        pass
print("--- END DIAGNOSTIC ---")
