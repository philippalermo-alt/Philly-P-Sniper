
import requests
import pandas as pd
import time
import os
from config import Config

# Target Leagues (All supported except 2.Bundesliga which has no xG)
LEAGUES = {
    'EPL': 39,
    'La Liga': 140,
    'Bundesliga': 78,
    'Serie A': 135,
    'Ligue 1': 61,
    'UCL': 2,
    'Europa': 3,
    'Championship': 40
}

SEASONS = [2024, 2025] # 2024-25 and 2025-26
OUTPUT_FILE = "soccer_xg_historical.csv"

def get_fixtures(league_id, season):
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&status=FT"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json().get('response', [])
        else:
            print(f"   ❌ Fixture Error {resp.status_code}: {resp.text}")
            return []
    except Exception as e:
        print(f"   ❌ Fixture Exception: {e}")
        return []

def get_fixture_stats(fixture_id):
    url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get('response', [])
        return []
    except:
        return []

def backfill_soccer():
    print(f"⚽️ Starting Soccer xG Backfill (Seasons: {SEASONS})...")
    
    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)
        processed_ids = set(existing_df['fixture_id'].unique())
        print(f"   ℹ️ Resuming... {len(processed_ids)} fixtures already in DB.")
    else:
        processed_ids = set()
        # Initialize file with headers
        pd.DataFrame(columns=[
            'league_name', 'league_id', 'fixture_id', 'date', 
            'home_team', 'away_team', 'home_goals', 'away_goals',
            'home_xg', 'away_xg'
        ]).to_csv(OUTPUT_FILE, index=False)
        
    for name, lid in LEAGUES.items():
        print(f"\n🌍 League: {name} (ID: {lid})")
        
        for season in SEASONS:
            print(f"   📅 Season {season}...")
            fixtures = get_fixtures(lid, season)
            print(f"      Found {len(fixtures)} completed matches.")
            
            for fix in fixtures:
                fid = fix['fixture']['id']
                if fid in processed_ids:
                    continue
                    
                match_date = fix['fixture']['date']
                home_team = fix['teams']['home']['name']
                away_team = fix['teams']['away']['name']
                home_goals = fix['goals']['home']
                away_goals = fix['goals']['away']
                
                # Fetch Stats
                print(f"   Fetching Stats: {home_team} vs {away_team} ... ", end="", flush=True)
                stats = get_fixture_stats(fid)
                
                # Parse xG
                home_xg = None
                away_xg = None
                
                # API returns list of 2 teams
                for tm in stats:
                    is_home = (tm['team']['name'] == home_team) # Simple name match, usually robust enough or use ID
                    # Actually API returns team ID, safer to match ID if possible, but let's look for 'expected_goals'
                    if not tm.get('statistics'): continue
                    
                    xg = next((x['value'] for x in tm['statistics'] if x['type'] == 'expected_goals'), None)
                    
                    # Assign to correct side (API order varies? usually Home first but not guaranteed)
                    # Let's match by team ID from fixture
                    if tm['team']['id'] == fix['teams']['home']['id']:
                        home_xg = xg
                    elif tm['team']['id'] == fix['teams']['away']['id']:
                        away_xg = xg
                
                if home_xg is not None or away_xg is not None:
                    # Save Row
                    row = {
                        'league_name': name,
                        'league_id': lid,
                        'fixture_id': fid,
                        'date': match_date,
                        'home_team': home_team,
                        'away_team': away_team,
                        'home_goals': home_goals,
                        'away_goals': away_goals,
                        'home_xg': home_xg,
                        'away_xg': away_xg
                    }
                    pd.DataFrame([row]).to_csv(OUTPUT_FILE, mode='a', header=False, index=False)
                    print(f"✅ Saved (xG: {home_xg} - {away_xg})")
                else:
                    print(f"⚠️ No xG found.")
                
                time.sleep(0.3) # Rate limit protection (API-Football allows 10/sec on Pro, but let's be safe with 3/sec)
            
    print("\n✅ Soccer Backfill Complete.")

if __name__ == "__main__":
    backfill_soccer()
