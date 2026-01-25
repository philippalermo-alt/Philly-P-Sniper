import pandas as pd

# Files
ROLLING_FILE = "mlb_pitcher_rolling_features.csv"
RAW_FILE = "mlb_statcast_2023_2025.csv"
OUTPUT_FILE = "mlb_rolling_features_with_targets.csv"

def append_targets():
    print("📉 Loading Rolling Features...")
    df_roll = pd.read_csv(ROLLING_FILE)
    df_roll['game_date'] = pd.to_datetime(df_roll['game_date'])
    
    print("⚾ Loading Raw Events (Target Gen)...")
    # Only need minimal cols
    df_raw = pd.read_csv(RAW_FILE, usecols=['game_date', 'pitcher', 'events', 'description'])
    df_raw['game_date'] = pd.to_datetime(df_raw['game_date'])
    
    # Calculate Ks per Pitcher-Game
    # Strikeout can be in 'events'='strikeout' OR 'description'='swinging_strike_blocked' if it completes K?
    # Safest: Use 'events' column which consolidates the AB result.
    
    # Filter for K events
    k_mask = df_raw['events'].isin(['strikeout', 'strikeout_double_play'])
    
    # GroupBy
    k_counts = df_raw[k_mask].groupby(['game_date', 'pitcher']).size().reset_index(name='actual_K')
    
    # Also calculate Total Pitches (Pitch Count Constraint)
    p_counts = df_raw.groupby(['game_date', 'pitcher']).size().reset_index(name='pitch_count')
    
    # Merge Targets back to Rolling Features
    print("🔗 Merging Targets...")
    df_final = pd.merge(df_roll, k_counts, on=['game_date', 'pitcher'], how='left')
    df_final = pd.merge(df_final, p_counts, on=['game_date', 'pitcher'], how='left')
    
    # Fill NaN Ks with 0 (if they pitched but got no Ks)
    df_final['actual_K'] = df_final['actual_K'].fillna(0)
    
    # Drop rows where we don't have pitch counts (implies data mismatch)
    df_final = df_final.dropna(subset=['pitch_count'])
    
    print(f"✅ Targets Appended. {len(df_final):,} rows ready for training.")
    print(df_final[['pitcher', 'actual_K', 'pitch_count']].head())
    
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    append_targets()
