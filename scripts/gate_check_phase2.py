
import pandas as pd
import os
from db.connection import get_db

def gate_check_phase2():
    print("🚧 STARTING PHASE 2 (GOALS) GATE CHECK 🚧")
    conn = get_db()
    
    # --- GATE A: PHASE 1 DEPENDENCY ---
    print("\n[GATE A] Phase 1 Dependency...")
    p1_model = "scripts/train_sog_model_nb.py"
    p1_out = "data/nhl_processed/sog_projections_phase1_nb.csv"
    
    if os.path.exists(p1_model) and os.path.exists(p1_out):
        print("✅ Phase 1 Artifacts Present.")
    else:
        print("❌ FAIL: Phase 1 Missing.")
        return

    # --- GATE B: SCHEMA ---
    print("\n[GATE B] Schema Checks...")
    
    # 1. Player Game (Goals, TOI)
    print("Checking 'nhl_player_game_logs'...")
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM public.nhl_player_game_logs LIMIT 1")
        cols = [desc[0] for desc in cur.description]
        print(f"Columns: {cols}")
        
        reqs = ['game_id', 'player_id', 'team', 'opponent', 'game_date', 'goals', 'toi_seconds']
        missing = [c for c in reqs if c not in cols]
        if missing:
            print(f"❌ FAIL: Missing Core Cols {missing}")
        else:
            print("✅ Core Player Cols Present.")
            
        # Check PP TOI
        if 'pp_toi' not in cols and 'pp_time_on_ice' not in cols:
             print("⚠️ CONDITIONAL: 'pp_toi' missing. (Will degrade precision).")
        
    except Exception as e:
        print(f"❌ FAIL: Table 'nhl_player_game_logs' error: {e}")

    # 2. Goalie Game
    print("Checking 'nhl_goalie_game_logs'...")
    try:
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'nhl_goalie_game_logs'")
        if cur.fetchone():
             print("✅ Goalie Table Exists.")
        else:
             print("❌ BLOCKED: 'nhl_goalie_game_logs' Table Missing.")
    except Exception as e:
        print(f"❌ Error checking goalie table: {e}")

    # 3. Shot Quality (xG/Types)
    # Check if xG is in player logs or separate table
    if 'ixg' in cols:
        print("✅ Shot Quality (ixG) in Player Logs.")
    else:
        print("❌ BLOCKED: 'ixg' (Shot Quality) missing from DB.")

    conn.close()
    print("\n🛑 PHASE 2 STATUS: CHECK LOGS ABOVE.")

if __name__ == "__main__":
    gate_check_phase2()
