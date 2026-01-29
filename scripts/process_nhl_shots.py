
import pandas as pd
import os

# Config
RAW_FILE = "data/raw/shots_2025.csv"
OUTPUT_FILE = "data/nhl_processed/player_game_stats_2025.parquet"

def process_shots():
    print(f"🚀 Loading {RAW_FILE}...")
    try:
        df = pd.read_csv(RAW_FILE)
    except Exception as e:
        print(f"❌ Failed to load raw file: {e}")
        return

    print(f"📊 Raw Rows: {len(df)}")
    
    # Opponent Logic
    df['opponent'] = df.apply(lambda x: x['awayTeamCode'] if x['teamCode'] == x['homeTeamCode'] else x['homeTeamCode'], axis=1)
    
    print("🔄 Aggregating metrics...")
    stats = df.groupby(['game_id', 'season', 'isPlayoffGame', 'shooterPlayerId', 'shooterName', 'teamCode', 'opponent', 'isHomeTeam']).agg(
        shots=('shotWasOnGoal', 'sum'),
        goals=('goal', 'sum'),
        ixg=('xGoal', 'sum'),
        attempts=('id', 'count'),
        missed=('event', lambda x: (x=='MISS').sum())
    ).reset_index()
    
    # Rename
    stats.rename(columns={
        'shooterPlayerId': 'player_id',
        'shooterName': 'player_name',
        'teamCode': 'team',
        'isHomeTeam': 'is_home'
    }, inplace=True)
    
    print(f"✅ Aggregated into {len(stats)} player-game records.")
    stats.to_parquet(OUTPUT_FILE)
    print(f"💾 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_shots()
