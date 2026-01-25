import requests
import json

GAME_ID = 2025020001

endpoints = [
    f"https://statsapi.web.nhl.com/api/v1/game/{GAME_ID}/boxscore",
    f"https://api-web.nhle.com/v1/game/{GAME_ID}/boxscore",
    f"https://api-web.nhle.com/v1/game/{GAME_ID}/landing",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
}

print(f"🔍 Probing Game ID: {GAME_ID}")

for url in endpoints:
    try:
        print(f"👉 Testing: {url}")
        r = requests.get(url, headers=headers, timeout=5)
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            print("   ✅ SUCCESS! Saving content...")
            filename = f"probe_{url.split('/')[-1]}.json"
            if 'api-web' in url: filename = "new_" + filename
            else: filename = "old_" + filename
            
            with open(filename, 'w') as f:
                json.dump(r.json(), f, indent=2)
            print(f"   💾 Saved to {filename}")
            
            # Check for Officials
            data = r.json()
            # Old API
            # data['liveData']['boxscore']['officials'] ?
            # New API
            # data['officials'] ?
            
            # Simply print keys to hint structure
            print(f"   Keys: {list(data.keys())}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    print("-" * 30)
