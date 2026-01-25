
import requests
from config import Config

def test_api_football_xg():
    print("🌍 Testing API-Football for xG Data...")
    
    if not Config.FOOTBALL_API_KEY:
        print("❌ Missing FOOTBALL_API_KEY in Config.")
        return

    # Fixture: Man City vs Nottingham Forest (Premier League, Dec 4, 2024)
    # Fixture ID: 1208036 (Example ID, hopefully valid or we search one)
    # Let's search for a recent fixture first to be safe, or just try a hardcoded guessed one?
    # Better: List fixtures for Man City (Team 50) and pick the last one.
    
    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    
    base_url = "https://v3.football.api-sports.io"
    
    # 1. Get Last Match for Man City (id 50)
    print("   Fetching last Man City match...")
    url = f"{base_url}/fixtures?team=50&last=1"
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if not data.get('response'):
            print(f"❌ No fixtures found. Msg: {data.get('message')}")
            # If msg is about subscription, we know.
            return
            
        fixture = data['response'][0]
        fix_id = fixture['fixture']['id']
        home = fixture['teams']['home']['name']
        away = fixture['teams']['away']['name']
        score = fixture['goals']
        
        print(f"   Found Match: {home} vs {away} (KB: {score['home']}-{score['away']}) [ID: {fix_id}]")
        
        # 2. Get Statistics
        print(f"   Fetching Statistics for Fixture {fix_id}...")
        stats_url = f"{base_url}/fixtures/statistics?fixture={fix_id}"
        
        s_resp = requests.get(stats_url, headers=headers, timeout=10)
        s_data = s_resp.json()
        
        if not s_data.get('response'):
            print("❌ No statistics data returned.")
            return
            
        # Response is list of 2 teams
        for team_stat in s_data['response']:
            team_name = team_stat['team']['name']
            stats = team_stat['statistics']
            
            # Look for xG
            xg = next((s['value'] for s in stats if s['type'] == 'expected_goals'), None)
            
            if xg is not None:
                print(f"✅ FOUND xG for {team_name}: {xg}")
            else:
                print(f"⚠️ No xG found for {team_name}. Available stats: {[s['type'] for s in stats[:5]]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api_football_xg()
