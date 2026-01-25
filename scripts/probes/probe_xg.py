import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

API_KEY = os.getenv('FOOTBALL_API_KEY')
LEAGUE_ID = 39 # EPL
SEASON = 2025 # Current season (2025-2026)

headers = {
    'x-apisports-key': API_KEY
}

def probe_player_xg():
    print("🕵️ Probing API-Football for Player xG...")
    
    # 1. Get a recent finished fixture
    # We look for the last round or just a date range
    today = datetime.now()
    last_week = today - timedelta(days=30)
    
    url = "https://v3.football.api-sports.io/fixtures"
    params = {
        'league': LEAGUE_ID,
        'season': SEASON,
        'from': last_week.strftime('%Y-%m-%d'),
        'to': today.strftime('%Y-%m-%d'),
        'status': 'FT' # Finished
    }
    
    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        
        if data['results'] == 0:
            print("⚠️ No recent EPL matches found. Trying wider date range...")
            # Fallback to hardcoded date if off-season or break
            # But EPL is usually active.
            return
            
        fixture = data['response'][0]
        match_id = fixture['fixture']['id']
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        
        print(f"⚽ Found Match: {home} vs {away} (ID: {match_id})")
        
        # 2. Get Player Stats for this match
        url_stats = "https://v3.football.api-sports.io/fixtures/players"
        params_stats = {'fixture': match_id}
        
        r_stats = requests.get(url_stats, headers=headers, params=params_stats)
        stats_data = r_stats.json()
        
        if stats_data['results'] == 0:
            print("❌ No player stats available for this match.")
            return

        # 3. Inspect Data Structure
        # Data is organized by Team -> Players -> Statistics
        
        found_xg = False
        
        for team_data in stats_data['response']:
            team_name = team_data['team']['name']
            print(f"\nChecking stats for {team_name}...")
            
            players = team_data['players']
            if not players: continue
            
            # Check first OUTFIELD player who played some minutes
            for p_entry in players:
                pos = p_entry['statistics'][0]['games']['position']
                if pos == 'G': continue # Skip Goalkeeper

                player_name = p_entry['player']['name']
                stats = p_entry['statistics'][0] 
                
                print(f"  - Inspecting {player_name} ({pos})...")
                print(f"    Available Stats Keys: {list(stats.keys())}")
                if 'goals' in stats:
                     print(f"    Goals Data: {stats['goals']}")
                break 
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    probe_player_xg()
