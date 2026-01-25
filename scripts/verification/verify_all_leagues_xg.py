
import requests
import time
from config import Config

def verify_all_leagues():
    print("🌍 Verifying xG Coverage for All Major Leagues...")
    
    if not Config.FOOTBALL_API_KEY:
        print("❌ Missing API Key")
        return

    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    base_url = "https://v3.football.api-sports.io"
    
    leagues = {
        'EPL': 39,
        'La Liga': 140,
        'Bundesliga': 78,
        'Serie A': 135,
        'Ligue 1': 61,
        'UCL': 2,
        'Championship': 40,
        '2.Bundesliga': 79
    }
    
    results = {}
    
    for name, lid in leagues.items():
        print(f"\n🔍 Checking {name} (ID: {lid})...")
        try:
            # Get last completed fixture
            url = f"{base_url}/fixtures?league={lid}&last=1&status=FT"
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if not data.get('response'):
                print(f"   ⚠️ No recent fixtures found.")
                results[name] = "No Fixtures"
                continue
                
            fixture = data['response'][0]
            fix_id = fixture['fixture']['id']
            matchup = f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}"
            print(f"   Fixture: {matchup} (ID: {fix_id})")
            
            # Get Stats
            stats_url = f"{base_url}/fixtures/statistics?fixture={fix_id}"
            s_resp = requests.get(stats_url, headers=headers, timeout=10)
            s_data = s_resp.json()
            
            found_xg = False
            for team_data in s_data.get('response', []):
                stats = team_data.get('statistics', [])
                xg = next((s['value'] for s in stats if s['type'] == 'expected_goals'), None)
                if xg is not None:
                    found_xg = True
                    print(f"   ✅ xG Found: {xg} ({team_data['team']['name']})")
                    break # One team is enough to prove coverage
            
            if found_xg:
                results[name] = "✅ YES"
            else:
                print(f"   ❌ xG NOT found in statistics payload.")
                # print(f"   Keys available: {[s['type'] for s in stats[:5]]}...")
                results[name] = "❌ NO"
                
            time.sleep(1) # Polite delay
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results[name] = "Error"

    print("\n📊 SUMMARY MATRIX:")
    print("-" * 30)
    for k, v in results.items():
        print(f"{k:<15} | {v}")
    print("-" * 30)

if __name__ == "__main__":
    verify_all_leagues()
