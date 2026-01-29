import pandas as pd
import os

FILE_PATH = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data/2024-25/goalies.csv"

def validate_granularity():
    if not os.path.exists(FILE_PATH):
        print(f"❌ File not found: {FILE_PATH}")
        return

    df = pd.read_csv(FILE_PATH)
    print(f"📂 Loaded {FILE_PATH}")
    print(f"📊 Total Rows: {len(df)}")
    
    # Check unique goalies
    unique_goalies = df['name'].nunique()
    print(f"🥅 Unique Goalies: {unique_goalies}")
    
    ratio = len(df) / unique_goalies
    print(f"➗ Rows per Goalie: {ratio:.2f}")
    
    # Check for Date or GameId columns
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'game' in c.lower()]
    print(f"📅 Potential Date/Game Columns: {date_cols}")
    
    if 'games_played' in df.columns:
        avg_gp = df['games_played'].mean()
        print(f"🕹 Average 'games_played' value: {avg_gp:.1f}")
        if avg_gp > 5:
            print("🚀 CONCLUSION: Data is SEASON AGGREGATED (Avg Games Played > 5 indicates summary stats).")
            print("❌ IMPOSSIBLE to map specific goalies to specific games using this file.")
        else:
            print("✅ CONCLUSION: Data might be Game Level.")
    else:
        print("❓ 'games_played' column missing.")

if __name__ == "__main__":
    validate_granularity()
