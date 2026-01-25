import requests
import json

# ESPN Game ID from nhl_backfill_final.csv
GAME_ID = "401801798"

url = f"https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={GAME_ID}"

print(f"🏒 Probing ESPN API for Game {GAME_ID}...")
try:
    r = requests.get(url, timeout=5)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        
        # Save Debug
        with open("debug_espn_summary.json", "w") as f:
            json.dump(data, f, indent=2)
        print("💾 Saved debug_espn_summary.json")
        
        # Check for Boxscore / Penalties
        # Usually data['boxscore']['teams'][0]['statistics'] or similar
        # Or data['gameInfo'] ?
        print(f"Keys: {list(data.keys())}")
        
        if 'boxscore' in data:
            print("✅ Boxscore found!")
            
except Exception as e:
    print(f"❌ Error: {e}")
