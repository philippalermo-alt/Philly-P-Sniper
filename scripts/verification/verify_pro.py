
import psycopg2
import pandas as pd
import os
from config import Config

def check():
    url = Config.DATABASE_URL
    if not url:
        print("❌ DATABASE_URL not set in Config.")
        return
        
    conn = psycopg2.connect(url)
    # Check for ANY pro system trigger
    # Removed 'market'
    df = pd.read_sql("SELECT timestamp, sport, teams, selection, trigger_type, sharp_score FROM intelligence_log WHERE trigger_type LIKE '%%PRO:%%' ORDER BY timestamp DESC LIMIT 10", conn)
    
    if df.empty:
        print("❌ NO PRO SYSTEM BETS FOUND IN DB.")
        # Check if we have that specific Stadium Under to see what its trigger IS
        df_chk = pd.read_sql("SELECT timestamp, teams, trigger_type, sharp_score FROM intelligence_log WHERE selection LIKE '%%Under%%' ORDER BY timestamp DESC LIMIT 5", conn)
        print("\nChecking Recent Unders specifically:")
        print(df_chk)
    else:
        print("✅ PRO SYSTEM BETS FOUND:")
        print(df)

if __name__ == "__main__":
    check()
