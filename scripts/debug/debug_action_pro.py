import requests
import re
import json
import os
from config import Config

def inspect_action_pro():
    if not Config.ACTION_COOKIE:
        print("❌ No ACTION_COOKIE found.")
        return

    headers = {
        'authority': 'www.actionnetwork.com',
        'accept': '*/*',
        'cookie': Config.ACTION_COOKIE.strip('"').strip("'"),
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    # 1. Get Build ID
    try:
        print("🔍 Fetching Build ID...")
        res = requests.get('https://www.actionnetwork.com/', headers=headers)
        match = re.search(r'"buildId":"(.*?)"', res.text)
        if not match:
            print("❌ Could not find Build ID")
            return
        build_id = match.group(1)
        print(f"✅ Build ID: {build_id}")
    except Exception as e:
        print(f"❌ Error fetching build ID: {e}")
        return

    # 2. Fetch NCAAB Data
    # The article mentioned NCAAB, so let's check that endpoint
    # URL structure from api_clients.py: https://www.actionnetwork.com/_next/data/{build_id}/ncaab/public-betting.json
    url = f"https://www.actionnetwork.com/_next/data/{build_id}/ncaab/public-betting.json"
    
    print(f"🔍 Fetching Data from: {url}")
    res = requests.get(url, headers=headers)
    
    if res.status_code != 200:
        print(f"❌ Failed to fetch data: {res.status_code}")
        return

    data = res.json()
    
    # 3. Save to file for inspection
    with open("action_network_dump.json", "w") as f:
        json.dump(data, f, indent=2)
        
    print("✅ Saved full JSON response to 'action_network_dump.json'.")
    
    # 4. Quick Scan for Keywords
    print("\n🔍 Scanning for Pro Keywords...")
    keywords = ["system", "pro", "signal", "sharp", "projection", "model", "edge"]
    
    def recursive_search(obj, path="root"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(x in k.lower() for x in keywords):
                    print(f"   found '{k}' at {path}")
                recursive_search(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_search(item, f"{path}[{i}]")

    # Limit depth/output for the log
    # We really strictly want to know if 'signals' or 'proSystems' exist in the games
    
    games = data.get('pageProps', {}).get('scoreboardResponse', {}).get('games', [])
    print(f"   Found {len(games)} games.")
    
    
    if games:
        sample_game = games[0]
        game_id = sample_game.get('id')
        print(f"   Testing PRO API for Game ID: {game_id}")
        
        
        # Test 3: Signals (Common for Sharp Report)
        sig_url = f"https://api.actionnetwork.com/web/v1/games/{game_id}/signals"
        print(f"   [3] GET {sig_url}")
        try:
            res_sig = requests.get(sig_url, headers=headers)
            print(f"      Status: {res_sig.status_code}")
            if res_sig.status_code == 200:
                print("      ✅ FOUND SIGNALS!")
                with open("signals_dump.json", "w") as f:
                    json.dump(res_sig.json(), f, indent=2)
        except Exception as e:
            print(f"      ❌ Error: {e}")

        # Test 4: Metadata (Might contain system matches)
        meta_url = f"https://api.actionnetwork.com/web/v1/games/{game_id}/metadata"
        print(f"   [4] GET {meta_url}")
        try:
            res_meta = requests.get(meta_url, headers=headers)
            print(f"      Status: {res_meta.status_code}")
        except:
             pass
    
if __name__ == "__main__":
    inspect_action_pro()
