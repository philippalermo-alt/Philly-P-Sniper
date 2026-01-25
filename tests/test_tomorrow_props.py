from understat_client import UnderstatClient
from player_props_model import PlayerPropsPredictor
from datetime import datetime, timedelta
import pandas as pd

def run_test():
    client = UnderstatClient(headless=True)
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    print(f"📅 Checking schedule for Tomorrow ({tomorrow})...")
    
    leagues = ["Bundesliga", "Serie_A", "Ligue_1", "La_liga", "EPL"]
    
    active_games = []
    
    for league in leagues:
        matches = client.get_league_matches(league, "2025")
        for m in matches:
            # Check date match
            # m['datetime'] is usually "2025-01-23 19:30:00"
            if m['datetime'].startswith(tomorrow):
                print(f"⚽ Found Game: {m['home_team']} vs {m['away_team']} ({league})")
                active_games.append({
                    "league": league,
                    "home": m['home_team'],
                    "away": m['away_team']
                })
                
    client.quit()
    
    if not active_games:
        print("⚠️ No games found for tomorrow. Checking Today just in case...")
        # Fallback to today for demo if tomorrow empty
        today = datetime.now().strftime('%Y-%m-%d')
        # ... logic ...
        return

    print("\n🔍 Scanning for Props in these leagues...")
    
    for Game in active_games:
        league = Game['league']
        teams = [Game['home'], Game['away']]
        
        print(f"\n💎 Analysis for {league}: {Game['home']} vs {Game['away']}")
        
        predictor = PlayerPropsPredictor(league=league, season="2025")
        props_df = predictor.scan_for_props_edges(min_minutes=300)
        
        if props_df.empty:
            print("   No data yet (Backfill might be pending).")
            continue
            
        # We can't filter by team_id easily (it's 'h'/'a').
        # So we show the Global Top 5 for the league.
        # The user can see if their player is on the list.
        
        print(f"   Top 5 Shot Volume (League Wide):")
        top_shots = props_df.sort_values("proj_shots_p90", ascending=False).head(5)
        print(top_shots[['player_name', 'proj_shots_p90', 'proj_xg_p90', 'sub_risk']])
        
        print(f"   Top 5 Playmakers (League Wide):")
        top_chain = props_df.sort_values("proj_xg_chain_p90", ascending=False).head(5)
        print(top_chain[['player_name', 'proj_xg_chain_p90', 'proj_xa_p90']])

if __name__ == "__main__":
    run_test()
