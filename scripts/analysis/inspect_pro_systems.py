import requests
import json
import os
from config import Config

def fetch_systems():
    if not Config.ACTION_COOKIE:
        print("❌ No ACTION_COOKIE found.")
        return

    headers = {
        'authority': 'api.actionnetwork.com',
        'accept': 'application/json, text/plain, */*',
        'cookie': Config.ACTION_COOKIE.strip('"').strip("'"),
        'origin': 'https://www.actionnetwork.com',
        'referer': 'https://www.actionnetwork.com/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    # Potential Endpoints based on typical REST patterns
    endpoints = [
        ("https://api.actionnetwork.com/web/v1/systems", "systems_list.json"),
        ("https://api.actionnetwork.com/web/v1/systems/featured", "systems_featured.json"),
        ("https://api.actionnetwork.com/web/v1/systems/user", "systems_user.json"), # Maybe systems the user follows?
    ]
    
    for url, filename in endpoints:
        print(f"🔍 Fetching: {url}...")
        try:
            res = requests.get(url, headers=headers)
            print(f"   Status: {res.status_code}")
            
            if res.status_code == 200:
                data = res.json()
                
                # Save full dump
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"   ✅ Saved to {filename}")
                
                # Peek at first item to see structure
                if isinstance(data, list) and len(data) > 0:
                    print(f"   Sample Item Keys: {list(data[0].keys())}")
                elif isinstance(data, dict):
                    print(f"   Root Keys: {list(data.keys())}")
            else:
                print(f"   ❌ Failed.")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    fetch_systems()
