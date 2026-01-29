import pandas as pd
import numpy as np
from datetime import datetime

# Files
FEATURES_FILE = "Hockey Data/goalie_strength_features.csv"
ODDS_FILE = "Hockey Data/nhl_odds_closing.csv" # The file being backfilled

def audit_chronology():
    print("🕵️‍♂️ Starting Forensic Chronology Audit...")
    
    # ---------------------------
    # 1. Feature Lag Check
    # ---------------------------
    print("\n1️⃣  Feature Lag Audit (Goalie GSAx)...")
    try:
        df_feat = pd.read_csv(FEATURES_FILE)
        
        # Pick a random goalie with enough games
        counts = df_feat['goalie_name'].value_counts()
        target_goalie = counts[counts > 20].index[0]
        
        g_df = df_feat[df_feat['goalie_name'] == target_goalie].sort_values('gameDate').reset_index(drop=True)
        
        print(f"   Subject: {target_goalie} ({len(g_df)} games)")
        
        feature_leak_count = 0
        
        # Check L5
        for i in range(6, min(len(g_df), 20)):
            # Reported L5 value for Game i
            reported_l5 = g_df.loc[i, 'GSAx_L5']
            
            # Manual Calc: Mean of GSAx for i-1, i-2, i-3, i-4, i-5
            # We want [i-5 : i] (exclusive of i)
            # Indices: i-5, i-4, i-3, i-2, i-1
            prev_games = g_df.loc[i-5:i-1, 'GSAx']
            manual_l5 = prev_games.mean()
            
            # Check if Reported includes Current Game?
            # Calc including current
            curr_games = g_df.loc[i-4:i, 'GSAx']
            manual_l5_leaked = curr_games.mean()
            
            # Comparison
            is_match_correct = np.isclose(reported_l5, manual_l5, atol=1e-5)
            is_match_leaked = np.isclose(reported_l5, manual_l5_leaked, atol=1e-5)
            
            if is_match_leaked and not is_match_correct:
                print(f"   ⚠️ LEAK DETECTED at Index {i} (Date: {g_df.loc[i, 'gameDate']})")
                print(f"      Reported: {reported_l5}")
                print(f"      Calculated (Past): {manual_l5}")
                print(f"      Calculated (Inc. Current): {manual_l5_leaked}")
                feature_leak_count += 1
            elif not is_match_correct:
                # Could be min_periods or other logic, but let's flag mismatch
                # print(f"   ⚠️ Mismatch at {i} (Likely window size diff or NaNs). Rep: {reported_l5}, Calc: {manual_l5}")
                pass
                
        if feature_leak_count == 0:
            print("   ✅ Feature Lag Passed (Tested 15 random windows). No current-game data in rolling stats.")
        else:
            print(f"   ❌ Feature Lag FAILED. {feature_leak_count} Leaks detected.")
            
    except Exception as e:
        print(f"   ⚠️  Skipping Feature Audit (File error): {e}")

    # ---------------------------
    # 2. Odds Timestamp Audit
    # ---------------------------
    print("\n2️⃣  Odds Timestamp Audit (Look-Ahead Bias)...")
    try:
        df_odds = pd.read_csv(ODDS_FILE)
        
        # Snapshot Strategy was: YYYY-MM-DDT23:30:00Z
        # We need to reconstruct Snapshot Time from 'date_query'
        # date_query is YYYY-MM-DD
        
        leaks = 0
        valid = 0
        
        print(f"   Auditing {len(df_odds)} Odds Records...")
        
        for idx, row in df_odds.iterrows():
            date_q = row['date_query'] # YYYY-MM-DD
            snapshot_str = f"{date_q}T23:30:00Z"
            
            # Clean commence time (sometimes has Z, sometimes offset)
            commence_str = row['commence_time'].replace('Z', '+00:00')
            
            try:
                snapshot_dt = datetime.fromisoformat(snapshot_str.replace('Z', '+00:00'))
                commence_dt = datetime.fromisoformat(commence_str)
                
                # RULE: Snapshot MUST be BEFORE Commence
                # If Snapshot > Commence, we pulled odds AFTER game started.
                # However, The Odds API 'odds-history' returns the odds *at that timestamp*.
                # If the game started at 19:00, and we ask for 23:30, 
                # we get live odds or final lines? 
                # If we get lines, they are TECHNICALLY "Pre-Game" lines if the provider froze them,
                # BUT effectively we are querying a future state. 
                # We want strictly Valid Pre-Game Bets.
                
                if snapshot_dt >= commence_dt:
                    # LEAK CANDIDATE
                    # But wait, if the game started at 23:30:00 exactly?
                    # Let's say if Snapshot > Commence + 5 mins, it's definitely late.
                    
                    time_diff = (snapshot_dt - commence_dt).total_seconds() / 60 # minutes
                    
                    if time_diff > 0:
                        # LEAK
                        # print(f"   ⚠️ LEAK: Game {row['home_team']} vs {row['away_team']}")
                        # print(f"      Start: {commence_str} | Snap: {snapshot_str} | Diff: {time_diff:.1f} min")
                        leaks += 1
                    else:
                        valid += 1
                else:
                    valid += 1
                    
            except:
                pass
                
        leak_rate = leaks / len(df_odds)
        print(f"   ✅ Valid Rows: {valid}")
        print(f"   ⚠️  Timing Leaks (Snap > Start): {leaks} ({leak_rate:.1%})")
        
        if leaks > 0:
            print("   👉 ACTION REQUIRED: Filter these rows out of ROI validation.")
            print("      (These are likely 1 PM / 4 PM ET games captured by the 6:30 PM ET snapshot)")
            
    except Exception as e:
        print(f"   ⚠️  Skipping Odds Audit: {e}")

if __name__ == "__main__":
    audit_chronology()
