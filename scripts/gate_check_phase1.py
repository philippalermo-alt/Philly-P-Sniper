
import pandas as pd
from db.connection import get_db

def gate_check():
    print("🚧 STARTING PHASE 1 GATE CHECK 🚧")
    conn = get_db()
    
    # Load Data
    query = "SELECT * FROM public.nhl_player_game_logs"
    df = pd.read_sql(query, conn)
    print(f"Loaded {len(df)} rows.")
    
    # --- GATE A: SCHEMA ---
    print("\n[GATE A] Schema Checks...")
    req_cols = ['game_id', 'player_id', 'shots', 'toi_seconds', 'team', 'opponent', 'game_date']
    missing = [c for c in req_cols if c not in df.columns]
    if missing:
        print(f"❌ FAIL: Missing cols {missing}")
        return
        
    # Uniqueness
    dups = df.duplicated(subset=['game_id', 'player_id']).sum()
    if dups > 0:
        print(f"❌ FAIL: {dups} Duplicate (game_id, player_id) keys found.")
        return
    print("✅ Schema Pass.")
    
    # --- GATE B: INTEGRITY ---
    print("\n[GATE B] Integrity Checks...")
    
    # SOG >= 0
    neg_sog = df[df['shots'] < 0]
    if not neg_sog.empty:
        print(f"❌ FAIL: {len(neg_sog)} rows with negative SOG.")
        return
        
    # TOI > 0 if SOG > 0
    # (If a player plays, TOI > 0. If SOG > 0, they MUST have played).
    # Exception: Data error where TOI=0 but SOG=1.
    sog_no_toi = df[(df['shots'] > 0) & (df['toi_seconds'] <= 0)]
    if not sog_no_toi.empty:
        print(f"❌ FAIL: {len(sog_no_toi)} rows with SOG>0 but TOI<=0.")
        print(sog_no_toi[['player_name', 'game_date', 'shots', 'toi_seconds']].head())
        # Determine strictness. User said "toi_total > 0 whenever sog > 0".
        return
        
    # Valid Teams (Optional strict check, just ensure not null)
    if df['team'].isnull().sum() > 0 or df['opponent'].isnull().sum() > 0:
        print("❌ FAIL: Null Team/Opponent.")
        return
        
    print("✅ Integrity Pass.")
    
    # --- GATE C: SAMPLE ---
    print("\n[GATE C] Sample Checks...")
    df['date'] = pd.to_datetime(df['game_date'])
    df['season'] = df['date'].dt.year # Approximate
    print(df['season'].value_counts().sort_index())
    
    missing_pct = df[req_cols].isnull().mean()
    print("Missingness %:")
    print(missing_pct[missing_pct > 0])
    
    print("\n🎉 ALL GATES PASSED. PROCEED TO PIPELINE.")

if __name__ == "__main__":
    gate_check()
