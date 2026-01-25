import argparse
import sys
from database import get_db
from features_soccer import compute_match_features

def validate_soccer_bet(home_team, away_team):
    print(f"🕵️‍♂️ Validating Match: {home_team} vs {away_team}")
    
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    cur = conn.cursor()
    
    # query to get match ID from team names (fuzzy or exact)
    # We need to find the most recent match between these two, or upcoming? 
    # Usually we want the UPCOMING match. But for backtesting we might want past.
    # The prompt implies using "backfilled" data, which is historical.
    # But for a validator, we likely want "Last Lineup" or "Season Avg"?
    # WAIT. The classifiers uses "Team Aggregates" from the *season*.
    # NOT just the specific match rows.
    # Actually, the user's prompt said: "From all players on a team in THAT match".
    # This implies we need the LINEUPS for the upcoming match.
    # If we don't have lineups, we use "Projected Lineup" (Top 11 by minutes).
    
    # Strategy:
    # 1. Fetch Season Stats for all players on Home Team
    # 2. Filter for "Likely Starters" (Top 14 by mins or recent starts)
    # 3. Use THOSE rows to build the feature vector.
    
    print("📊 Fetching season player stats...")
    
    # This query assumes a table 'understat_player_stats' or similar exists with season totals
    # We will aggregate from 'player_match_stats' if needed.
    # Let's assume we aggregate from the match logs we backfilled.
    
    sql_players = """
        SELECT 
            player_name, 
            SUM(minutes) as min,
            SUM(shots) as shots,
            SUM(goals) as goals,
            SUM(assists) as assists,
            SUM(xg) as "xG",
            SUM(xa) as "xA",
            SUM(xg_chain) as "xGChain",
            SUM(xg_buildup) as "xGBuildup"
        FROM player_stats
        WHERE team_name ILIKE %s
        GROUP BY player_name
        ORDER BY min DESC
        LIMIT 16  -- Take top 16 rotation players
    """
    
    try:
        # Home Team
        cur.execute(sql_players, (f"%{home_team}%",))
        cols = [desc[0] for desc in cur.description]
        home_rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        
        if not home_rows:
            print(f"⚠️ No data found for {home_team}")
            return

        # Away Team
        cur.execute(sql_players, (f"%{away_team}%",))
        away_rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        
        if not away_rows:
            print(f"⚠️ No data found for {away_team}")
            return
            
        print(f"✅ Loaded {len(home_rows)} players for {home_team}")
        print(f"✅ Loaded {len(away_rows)} players for {away_team}")
        
        # Compute Features
        feats = compute_match_features(home_rows, away_rows)
        
        # Scoring Logic (Duplicated from test script for now)
        MAX_XG_SUM = 5.0 * 38 # Season totals? No, we need per-matchavgs.
        # WAIT. The features_soccer computes SUMS.
        # If we feed it SEASON TOTALS, numbers will be huge.
        # We need PER 90 or PER MATCH averages.
        # The proposal said: "From all players on a team IN THAT MATCH".
        # So we should normalize season stats to "Per Match" (divide by games played? roughly).
        # Or just divide the final sums by number of matches?
        # Simpler: Divide all stats by (Total Team Minutes / 900) approx?
        # Let's normalize the features themselves.
        
        # Actually, let's normalize the INPUT rows to "Per 90" before feeding to feature computer?
        # No, 'features_soccer' sums them up.
        # Let's assume the input `home_rows` represent "The Expected Output of the Team in ONE Game".
        # So we should take the Season Totals and divide by Matches Played for each player?
        # Yes.
        
        # Quick Normalization (Season Total -> Per 90)
        # We assume 'min' is season minutes.
        for r in home_rows:
            m = r['min']
            if m > 0:
                factor = 90 / m
                for k in ['shots', 'goals', 'assists', 'xG', 'xA', 'xGChain', 'xGBuildup']:
                    r[k] = float(r[k]) * factor if r[k] else 0
            # Set min to 90 for the calculation
            r['min'] = 90
            
        for r in away_rows:
            m = r['min']
            if m > 0:
                factor = 90 / m
                for k in ['shots', 'goals', 'assists', 'xG', 'xA', 'xGChain', 'xGBuildup']:
                    r[k] = float(r[k]) * factor if r[k] else 0
            r['min'] = 90
            
        # NOW compute features on these "Per 90" projections
        feats = compute_match_features(home_rows, away_rows)
        
        # --- Scoring ---
        # (Same constants as test script, which were based on single match values)
        MAX_XG_SUM = 4.5
        MAX_SHOTS_SUM = 35.0
        MAX_CHAIN_SUM = 5.0
        MAX_BUILDUP_SUM = 3.5
        MAX_FRAGILITY = 1.0 
        MAX_BALANCE = 1.5
        
        n_xg = min(feats['xG_sum'] / MAX_XG_SUM, 1.0)
        n_shots = min(feats['shots_sum'] / MAX_SHOTS_SUM, 1.0)
        n_chain = min(feats['chain_sum'] / MAX_CHAIN_SUM, 1.0)
        n_buildup = min(feats['buildup_sum'] / MAX_BUILDUP_SUM, 1.0)
        n_fragility = min(feats['fragility_sum_top1xG'] / 1.5, 1.0)
        score_fragility = 1.0 - n_fragility
        n_balance = min(feats['balance_xG_abs'] / MAX_BALANCE, 1.0)
        score_balance = 1.0 - n_balance
        
        raw_score = (
            (0.35 * n_xg) +
            (0.20 * n_shots) +
            (0.15 * n_chain) +
            (0.10 * n_buildup) +
            (0.10 * score_fragility) +
            (0.10 * score_balance)
        ) * 100
        
        print("\n--- 🧠 Model Classification ---")
        print(f"Projected xG Sum: {feats['xG_sum']:.2f}")
        print(f"Fragility Score: {score_fragility:.2f}")
        print(f"Over Score: {raw_score:.1f} / 100")
        
        if raw_score > 70: print("✅ PLAY OVER 2.5")
        elif raw_score >= 55: print("🤔 LEAN OVER")
        else: print("🛑 LEAN UNDER / PASS")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    args = parser.parse_args()
    
    validate_soccer_bet(args.home, args.away)
