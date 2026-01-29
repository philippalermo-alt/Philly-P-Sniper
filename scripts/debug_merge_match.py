
import pandas as pd
from db.connection import get_db

CSV_FILE = "data/nhl_processed/player_game_stats_mnp_2025.csv"

def debug_match():
    print("🔍 Debugging Merge Match...")
    conn = get_db()
    
    # Get Valid DB Keys
    q = "SELECT game_id, player_name FROM public.nhl_player_game_logs WHERE game_id LIKE '2025%'"
    db_df = pd.read_sql(q, conn)
    print(f"DB Season 2025 Rows: {len(db_df)}")
    if len(db_df) > 0:
        print("Sample DB Keys:")
        print(db_df.head())
        
    # Get CSV Keys
    csv_df = pd.read_csv(CSV_FILE)
    print(f"CSV Rows: {len(csv_df)}")
    print("Sample CSV Keys:")
    print(csv_df[['full_game_id', 'player_name']].head())
    csv_df['gid'] = csv_df['full_game_id'].astype(str)
    
    # Check Intersection
    common_ids = set(db_df['game_id']).intersection(set(csv_df['gid']))
    print(f"Common GameIDs: {len(common_ids)}")
    
    common_names = set(db_df['player_name']).intersection(set(csv_df['player_name']))
    print(f"Common Names: {len(common_names)}")
    
    # Check Exact Pairs
    db_pairs = set(zip(db_df['game_id'], db_df['player_name']))
    csv_pairs = set(zip(csv_df['gid'], csv_df['player_name']))
    
    common = db_pairs.intersection(csv_pairs)
    print(f"Common Pairs (Game+Player): {len(common)}")
    
    if len(common) < 100:
        print("Mismatches found. Examples:")
        sample_gid = list(common_ids)[0] if common_ids else "None"
        print(f"Checking GameID {sample_gid}:")
        print("DB Players:", db_df[db_df['game_id']==sample_gid]['player_name'].values)
        print("CSV Players:", csv_df[csv_df['gid']==sample_gid]['player_name'].values)

if __name__ == "__main__":
    debug_match()
