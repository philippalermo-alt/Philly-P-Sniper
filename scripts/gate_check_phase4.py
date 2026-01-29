
import pandas as pd
import os

def gate_check_phase4():
    print("🚧 STARTING PHASE 4 (POINTS) GATE CHECK 🚧")
    
    # 1. Define Sources
    p1_file = "data/nhl_processed/sog_projections_phase1_nb.csv"
    p2_file = "data/nhl_processed/goal_projections_phase2.csv"
    p3_file = "data/nhl_processed/assist_projections_phase3.csv"
    
    # 2. Check Existence
    if not all(os.path.exists(f) for f in [p1_file, p2_file, p3_file]):
        print("❌ FAIL: Missing Upstream Projections.")
        return
    else:
        print("✅ Upstream Artifacts Present.")
        
    # 3. Load & Check Schema
    df1 = pd.read_csv(p1_file)
    df2 = pd.read_csv(p2_file)
    df3 = pd.read_csv(p3_file)
    
    print(f"Phase 1 Rows: {len(df1)}")
    print(f"Phase 2 Rows: {len(df2)}")
    print(f"Phase 3 Rows: {len(df3)}")
    
    # Check Critical Cols
    # Phase 1: pred_mu
    # Phase 2: pred_prob_goal (or we derived prob_goal_1plus, need to ensure we have p_conv or derived it)
    # Wait, Phase 2 CSV columns: ['player_name', 'game_date', 'pred_mu', 'pred_prob_goal', 'prob_goal_1plus', 'prob_goal_2plus']
    # Phase 3 CSV columns: ['player_name', 'game_date', 'pred_mu', 'prob_ast_1plus', 'prob_ast_2plus']
    
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    cols3 = set(df3.columns)
    
    if 'pred_mu' not in cols1: print("❌ P1 Missing 'pred_mu'"); return
    if 'pred_prob_goal' not in cols2: print("❌ P2 Missing 'pred_prob_goal'"); return
    if 'pred_mu' not in cols3: print("❌ P3 Missing 'pred_mu'"); return
    
    print("✅ Required Columns Present.")
    
    # 4. Integration Check (Matching Keys)
    # Join on player_name, game_date
    # Note: Phase 1 CSV keys: player_name, game_date.
    
    # Ensure date formats match (String yyyy-mm-dd)
    df1['key'] = df1['player_name'] + "_" + df1['game_date']
    df2['key'] = df2['player_name'] + "_" + df2['game_date']
    df3['key'] = df3['player_name'] + "_" + df3['game_date']
    
    common = set(df1['key']).intersection(df2['key']).intersection(df3['key'])
    print(f"Common Rows (Intersection): {len(common)}")
    
    if len(common) < 1000:
        print("❌ FAIL: Low Overlap between phases.")
        return
        
    print("✅ Integration Pass.")
    print("🏁 PHASE 4 GATE STATUS: PASS.")

if __name__ == "__main__":
    gate_check_phase4()
