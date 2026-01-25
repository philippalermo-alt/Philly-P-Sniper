import requests
import re
import json
import os
from config import Config

def inspect_page_source():
    if not Config.ACTION_COOKIE:
        print("❌ No ACTION_COOKIE found.")
        return

    headers = {
        'authority': 'www.actionnetwork.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'cookie': Config.ACTION_COOKIE.strip('"').strip("'"),
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # Target URL: https://www.actionnetwork.com/pro-systems/discover
    url = "https://www.actionnetwork.com/pro-systems/discover"
    print(f"🔍 Fetching HTML: {url}...")
    
    try:
        res = requests.get(url, headers=headers)
        print(f"   Status: {res.status_code}")
        
        if res.status_code == 200:
            html = res.text
            
            # NEW STRATEGY: Parse <script id="__NEXT_DATA__" type="application/json">
            print("   🔍 Searching for __NEXT_DATA__...")
            
            data_match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if data_match:
                json_str = data_match.group(1)
                try:
                    data = json.loads(json_str)
                    print("   ✅ FOUND __NEXT_DATA__!")
                    
                    with open("next_data_dump.json", "w") as f:
                        json.dump(data, f, indent=2)
                    print("      Saved to 'next_data_dump.json'")
                    
                    # Quick Scan
                    props = data.get('props', {}).get('pageProps', {})
                    print(f"      Page Props Keys: {list(props.keys())}")
                    
                except Exception as e:
                    print(f"      ❌ JSON Parse Error: {e}")
            else:
                print("   ❌ Could not find __NEXT_DATA__ script tag.")
                
                
        else:
            print(f"   ❌ HTML Fetch Failed.")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    inspect_page_source()
