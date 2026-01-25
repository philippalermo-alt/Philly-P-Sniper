import pandas as pd
import numpy as np

INPUT_FILE = "nhl_ref_game_logs_v2.csv"
OUTPUT_FILE = "nhl_ref_stats_2025_26.csv"
K_FACTOR = 20  # Shrinkage weight (games)

def calculate_shrinkage(df):
    if df.empty:
        print("❌ No data found.")
        return

    print(f"📊 Processing {len(df)} games...")
    
    # 1. League Averages
    avg_pen = df['total_penalties'].mean()
    avg_ppo = df['total_ppo'].mean()
    avg_home_diff = df['home_pp_diff'].mean()
    
    print(f"   League Avg Penalties: {avg_pen:.2f}")
    print(f"   League Avg PPO: {avg_ppo:.2f}")
    
    # 2. Explode Refs (Ref1, Ref2 -> single column 'Referee')
    refs_1 = df[['Ref1', 'total_penalties', 'total_ppo', 'home_pp_diff']].copy().rename(columns={'Ref1': 'Referee'})
    refs_2 = df[['Ref2', 'total_penalties', 'total_ppo', 'home_pp_diff']].copy().rename(columns={'Ref2': 'Referee'})
    
    all_refs = pd.concat([refs_1, refs_2]).dropna(subset=['Referee'])
    
    # 3. Aggregate per Ref
    ref_stats = all_refs.groupby('Referee').agg(
        games=('total_penalties', 'count'),
        raw_avg_pen=('total_penalties', 'mean'),
        raw_avg_ppo=('total_ppo', 'mean'),
        raw_avg_home_diff=('home_pp_diff', 'mean')
    ).reset_index()
    
    # 4. Apply Shrinkage
    # Formula: (games * raw + k * league_avg) / (games + k)
    
    def shrink(row, raw_col, league_avg):
        n = row['games']
        raw = row[raw_col]
        return (n * raw + K_FACTOR * league_avg) / (n + K_FACTOR)

    ref_stats['shrunk_pen'] = ref_stats.apply(lambda x: shrink(x, 'raw_avg_pen', avg_pen), axis=1)
    ref_stats['shrunk_ppo'] = ref_stats.apply(lambda x: shrink(x, 'raw_avg_ppo', avg_ppo), axis=1)
    ref_stats['shrunk_home_diff'] = ref_stats.apply(lambda x: shrink(x, 'raw_avg_home_diff', avg_home_diff), axis=1)
    
    # Sort by 'Active' (games > 0)
    ref_stats = ref_stats.sort_values('games', ascending=False)
    
    print(f"✅ Calculated stats for {len(ref_stats)} referees.")
    
    # Save
    ref_stats.to_csv(OUTPUT_FILE, index=False)
    print(f"💾 Saved to {OUTPUT_FILE}")
    
    # Preview Top 5 High-Penalty Refs
    print("\n🚨 Top 5 'Hanging' Refs (High Penalties):")
    print(ref_stats.sort_values('shrunk_pen', ascending=False).head(5)[['Referee', 'games', 'shrunk_pen']])

if __name__ == "__main__":
    import os
    if os.path.exists(INPUT_FILE):
        df = pd.read_csv(INPUT_FILE)
        calculate_shrinkage(df)
    else:
        print(f"❌ Input file {INPUT_FILE} not found. Run expander first.")
