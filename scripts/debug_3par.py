import pandas as pd
from db.connection import get_db

def check():
    conn = get_db()
    
    print("Checking nba_historical_games...")
    df_games = pd.read_sql("SELECT game_id, home_3par, away_3par FROM nba_historical_games LIMIT 10", conn)
    print(df_games)
    
    print("\nChecking nba_model_train...")
    df_train = pd.read_sql("SELECT game_id, h_sea_3par, threept_mismatch FROM nba_model_train LIMIT 10", conn)
    print(df_train)
    
    conn.close()

if __name__ == "__main__":
    check()
