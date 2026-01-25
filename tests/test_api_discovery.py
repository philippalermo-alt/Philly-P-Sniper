import requests
import json

GAME_ID = 2025020001

# List of potential URL patterns to probe
endpoints = [
    f"https://api-web.nhle.com/v1/game/{GAME_ID}/landing",
    f"https://api-web.nhle.com/v1/game/{GAME_ID}/boxscore",
    f"https://api-web.nhle.com/v1/wsc/game-story/{GAME_ID}",
    f"https://api.nhle.com/stats/rest/en/game/{GAME_ID}/boxscore",
    f"https://api.nhle.com/stats/rest/en/game/{GAME_ID}/feed/live",
    f"https://api.nhle.com/stats/rest/en/game/{GAME_ID}/linescore",
    # Try the link from the schedule (GameCenter)?
    # /gamecenter/chi-vs-fla/2025/10/07/2025020001
    f"https://api-web.nhle.com/v1/gamecenter/chi-vs-fla/2025/10/07/{GAME_ID}",
    f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/landing",
    f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/boxscore",
    f"https://api-web.nhle.com/v1/gamecenter/{GAME_ID}/play-by-play",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Accept": "application/json"
}

print(f"🔍 Discovery Probe for Game ID: {GAME_ID}")

found_any = False

for url in endpoints:
    try:
        print(f"👉 Testing: {url}")
        r = requests.get(url, headers=headers, timeout=5)
        print(f"   Status: {r.status_code}")
        
        if r.status_code == 200:
            found_any = True
            print("   ✅ SUCCESS! Saving content...")
            filename = f"discovery_{url.split('/')[-1]}.json"
            # Sanitize filename
            filename = filename.replace("?", "_").replace("=", "_")
            
            # Simple content check
            try:
                data = r.json()
                print(f"   Keys: {list(data.keys())[:5]}")
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"   💾 Saved to {filename}")
            except:
                print("   ⚠️ Response not JSON")
                
    except Exception as e:
        print(f"   ❌ Network Error: {e}")
    print("-" * 30)

if not found_any:
    print("❌ All probes failed.")
else:
    print("✅ At least one endpoint worked.")
