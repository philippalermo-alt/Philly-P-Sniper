
import pandas as pd
from db.connection import get_db

def gate_check_phase3():
    print("🚧 STARTING PHASE 3 (ASSISTS) GATE CHECK 🚧")
    conn = get_db()
    
    # --- GATE A: SCHEMA ---
    print("\n[GATE A] Schema Checks...")
    cur = conn.cursor()
    cur.execute("SELECT * FROM public.nhl_player_game_logs LIMIT 1")
    cols = [desc[0] for desc in cur.description]
    print(f"Columns: {cols}")
    
    reqs = ['game_id', 'player_id', 'assists', 'toi_seconds']
    missing = [c for c in reqs if c not in cols]
    if missing:
        print(f"❌ FAIL: Missing Cols {missing}")
        return
    else:
        print("✅ Core Assist Cols Present.")
        
    if 'pp_toi' in cols:
        print("✅ 'pp_toi' column exists (Populated? Check Ingest).")
    else:
        print("⚠️ CONDITIONAL: 'pp_toi' missing.")

    # --- GATE B: INTEGRITY (Reconciliation) ---
    print("\n[GATE B] Integrity Checks (Reconciliation)...")
    
    # Load Game Aggregates
    q = """
        SELECT game_id, 
               SUM(goals) as total_goals, 
               SUM(assists) as total_assists,
               COUNT(*) as players
        FROM public.nhl_player_game_logs
        GROUP BY game_id
    """
    agg = pd.read_sql(q, conn)
    
    if len(agg) == 0:
        print("❌ FAIL: No Data in DB.")
        return
        
    print(f"Analyzed {len(agg)} Games.")
    
    # Check 1: Assists vs Goals
    # Assists should be roughly 1.0 to 2.0 * Goals (Primary + Secondary).
    # Some unassisted goals exist.
    # If Total Goals > 0, Total Assists should be > 0 (usually).
    
    agg['ratio'] = agg['total_assists'] / agg['total_goals'].replace(0, 1) # Avoid div/0
    
    zero_assist_games = agg[(agg['total_goals'] > 0) & (agg['total_assists'] == 0)]
    if len(zero_assist_games) > 0:
        print(f"⚠️ Warning: {len(zero_assist_games)} games have Goals but 0 Assists.")
        # This might be valid (all unassisted?) but rare.
        
    avg_ratio = agg['ratio'].mean()
    print(f"Average Assists/Goal Ratio: {avg_ratio:.2f} (Expected ~1.7)")
    
    if avg_ratio < 1.0:
        print("⚠️ CONDITIONAL: Low Assist Ratio. Ensure Secondaries are tracked.")
    else:
        print("✅ Assist Ratio Healthy.")
        
    # Check 2: Negatives
    neg_check = pd.read_sql("SELECT count(*) FROM public.nhl_player_game_logs WHERE assists < 0", conn)
    if neg_check.iloc[0,0] > 0:
         print("❌ FAIL: Negative Assists Found.")
         return
         
    print("✅ Integrity Pass.")
    
    conn.close()
    print("\n🏁 PHASE 3 GATE STATUS: CHECK LOGS.")

if __name__ == "__main__":
    gate_check_phase3()
