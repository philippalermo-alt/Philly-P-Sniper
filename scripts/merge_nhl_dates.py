
import pandas as pd

STATS_FILE = "data/nhl_processed/player_game_stats_2025.parquet"
TEAMS_FILE = "data/raw/all_teams.csv"
OUTPUT_FILE = "data/nhl_processed/player_game_stats_mnp_2025.csv"

def merge_dates():
    print(f"🚀 Loading Stats: {STATS_FILE}")
    stats_df = pd.read_parquet(STATS_FILE)
    
    print(f"🚀 Loading Schedule: {TEAMS_FILE}")
    teams_df = pd.read_csv(TEAMS_FILE)
    
    # Construct Full ID in Stats
    def make_id(row):
        # Shots ID: 20001 (5 digits).
        # Target: 2025020001 (10 digits).
        # Need to insert '0' before the game_id string?
        # 2025 + 0 + 20001 = 2025020001.
        season = str(int(row['season']))
        gid = str(int(row['game_id'])) # "20001"
        full = season + "0" + gid
        return int(full)

    print("🔨 Constructing IDs (Fixed)...")
    stats_df['full_game_id'] = stats_df.apply(make_id, axis=1)
    
    # Map from Schedule
    date_map = teams_df[['gameId', 'gameDate']].drop_duplicates()
    date_map.rename(columns={'gameId': 'full_game_id', 'gameDate': 'date'}, inplace=True)
    
    print("🔄 Merging...")
    merged = pd.merge(stats_df, date_map, on='full_game_id', how='left')
    
    missing = merged['date'].isnull().sum()
    print(f"⚠️ Missing Dates: {missing} / {len(merged)}")
    
    if missing == 0:
        print("✅ SUCCESS: All dates mapped.")
    else:
        print("❌ Still missing dates.")
        print("Sample Missing:", merged[merged['date'].isnull()]['full_game_id'].unique()[:3])

    merged.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    merge_dates()
