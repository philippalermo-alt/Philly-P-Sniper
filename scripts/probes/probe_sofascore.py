import requests
import json
import time

def probe_sofascore():
    # IDs derived from user URL: .../premier-league/17#id:76986
    TOURNAMENT_ID = 17
    SEASON_ID = 76986
    
    # SofaScore API endpoints (Reverse engineered)
    # They often rotate or require hash, but let's try standard ones.
    
    endpoints = [
        # 1. Top Players by xG (The jackpot)
        f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/statistics/overall",
        # 2. Top Scorer list (often contains xG)
        f"https://api.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/top-players/expectedGoals",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.sofascore.com/',
        'Origin': 'https://www.sofascore.com',
        'Accept': '*/*'
    }

    print(f"🕵️ Probing SofaScore API for Season {SEASON_ID}...")

    for url in endpoints:
        print(f"\nTrying: {url}")
        try:
            r = requests.get(url, headers=headers, timeout=5)
            print(f"Status: {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                # Check for player xG data
                if 'topPlayers' in data:
                    print("✅ Found Top Players Data!")
                    players = data['topPlayers']
                    for p in players[:3]:
                        name = p['player']['name']
                        xg = p.get('statistics', {}).get('expectedGoals')
                        rating = p.get('statistics', {}).get('rating')
                        print(f"  - {name}: xG {xg}, Rating {rating}")
                elif 'statistics' in data:
                    print("✅ Found Statistics Data!")
                    # Inspect first few keys
                    print(f"Keys: {list(data['statistics'][0].keys()) if isinstance(data['statistics'], list) else 'Dict'}")
            else:
                print("❌ Failed (likely Cloudflare or invalid headers)")
        
        except Exception as e:
            print(f"❌ Error: {e}")
        
        time.sleep(1) # Be polite

if __name__ == "__main__":
    probe_sofascore()
