
import pandas as pd
import numpy as np

SHOTS_FILE = "data/raw/shots_2025.csv"
TEAMS_FILE = "data/raw/all_teams.csv"

def sanity_check():
    print("🕵️‍♀️ Starting Sanity Check...\n")
    
    # --- 1. GAME TABLE ---
    print("--- 1. Game Table (all_teams.csv) ---")
    try:
        games = pd.read_csv(TEAMS_FILE)
        # Filter 2024 season (which represents 2024-2025 usually? or 2025? MoneyPuck uses start year?)
        # Let's check season values.
        print(f"Seasons found: {sorted(games['season'].unique())}")
        
        # Check Unique GameIDs
        dupes = games['gameId'].duplicated().sum() # Should be dups because Home/Away?
        # GameId key should be unique per game? No, per ROW.
        # But One Row Per Game?
        # Usually a game has 2 keys (Home perspective, Away perspective) in this file?
        # Let's check.
        # Step 3191: NYR vs TB. 2 rows shown? No, 1 row shown `NYR... AWAY`.
        # Maybe 1 row per team per game.
        n_rows = len(games)
        n_unique = games['gameId'].nunique()
        print(f"Rows: {n_rows}, Unique Games: {n_unique}. Ratio: {n_rows/n_unique:.2f}")
        if n_rows == n_unique * 2:
            print("✅ 2 Rows per Game (Home/Away) confirmed.")
        else:
            print(f"⚠️ Ratio is {n_rows/n_unique:.2f} (Expected 2.0)")

        # Date Check
        if 'gameDate' in games.columns:
             # Check format
             print("Sample Dates:", games['gameDate'].head().values)
             # Future Check
             games['dt'] = pd.to_datetime(games['gameDate'], format='%Y%m%d', errors='coerce')
             future = games[games['dt'] > pd.Timestamp.now()]
             if not future.empty:
                 print(f"⚠️ Found {len(future)} future games.")
             else:
                 print("✅ No future dates found.")
    except Exception as e:
        print(f"❌ Game Table Error: {e}")

    # --- 2. PLAYER-GAME TABLE ---
    print("\n--- 2. Player-Game Table (From Shots) ---")
    try:
        shots = pd.read_csv(SHOTS_FILE, nrows=10000) # Sample
        
        # Unique Key Check
        # We aggregate this, so we check raw columns.
        print(f"Raw Columns: {list(shots.columns)}")
        
        # TOI CHECK (CRITICAL)
        if 'shooterTimeOnIce' in shots.columns:
            print("found 'shooterTimeOnIce'. Stats:")
            print(shots['shooterTimeOnIce'].describe())
            # Check if consistent per player-game?
            # Or is it time OF the shot?
            # Let's group by player-game and see var.
            # We can't grouping strictly without game_id mapping issues, but let's try raw game_id
            g = shots.groupby(['game_id', 'shooterPlayerId'])['shooterTimeOnIce']
            # If it's Total TOI, min SHOULD equal max (constant).
            # If it's timestamp, max > min.
            
            diffs = g.max() - g.min()
            print(f"TOI Variation within Game (Mean Diff): {diffs.mean():.2f}")
            if diffs.mean() > 10: 
                print("❌ 'shooterTimeOnIce' varies significantly. It is likely TIME OF SHOT, not TOTAL TOI.")
                print("⚠️ **CRITICAL GAP**: We lack Total Game TOI per player.")
            else:
                print("✅ 'shooterTimeOnIce' is constant. It represents Total TOI.")
        else:
             print("❌ 'shooterTimeOnIce' MISSING.")

        # SOG / Goals Consistency
        # Goals <= SOG?
        # In this file, SOG is a flag `shotWasOnGoal`. Goal is `goal`.
        # If goal=1, shotWasOnGoal SHOULD be 1.
        invalid_goals = shots[(shots['goal']==1) & (shots['shotWasOnGoal']==0)]
        if not invalid_goals.empty:
            print(f"⚠️ Found {len(invalid_goals)} goals not marked as SOG.")
        else:
            print("✅ All goals are SOG.")

    except Exception as e:
        print(f"❌ Player Table Error: {e}")

if __name__ == "__main__":
    sanity_check()
