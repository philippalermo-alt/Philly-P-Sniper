
import requests
from config import Config

def test_team_stats():
    print("🌍 Testing API-Football Team Statistics Endpoint...")
    
    if not Config.FOOTBALL_API_KEY:
        print("❌ Missing FOOTBALL_API_KEY.")
        return

    headers = {
        'x-rapidapi-host': "v3.football.api-sports.io",
        'x-rapidapi-key': Config.FOOTBALL_API_KEY
    }
    
    base_url = "https://v3.football.api-sports.io"
    
    # Premier League (39) - 2024 Season
    # Man City (50)
    url = f"{base_url}/teams/statistics?league=39&season=2024&team=50"
    
    print(f"   Fetching stats for Man City (PL 2024)...")
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        
        if not data.get('response'):
            print(f"❌ No response. Msg: {data.get('message')}")
            return
            
        stats = data['response']
        
        # Check for 'goals' -> 'for' -> 'average'
        goals = stats.get('goals', {})
        print(f"   Goals For (Total): {goals.get('for', {}).get('total', {}).get('total')}")
        
        # Is there xG?
        # Typically under 'goals' or top level?
        # Let's dump keys
        # print("   Keys:", stats.keys())
        
        # Sometimes API-Football puts xG logic elsewhere or doesn't have it in aggregate.
        # Let's specifically look for 'expected_goals' string in the full text dump to be sure
        import json
        text_dump = json.dumps(stats)
        
        if "expected_goals" in text_dump or "xg" in text_dump.lower():
            print("✅ FOUND 'expected_goals' in Season Stats!")
            # Try to locate it
            # It's usually not in the standard /teams/statistics response for free tier?
            # Let's print a snippet if found
        else:
            print("❌ 'expected_goals' NOT found in Season Stats.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_team_stats()
