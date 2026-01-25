import requests
import re
import json
import codecs

def probe_understat(match_id="28989"):
    url = f"https://understat.com/match/{match_id}"
    print(f"🕵️ Probing Understat URL: {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            print(f"❌ Failed to fetch page: {res.status_code}")
            return

        html = res.text
        print(f"📄 HTML Length: {len(html)}")
        print(f"📄 Header Preview:\n{html[:500]}")
        
        # Understat stores data in scripts like:
        # var rosterData = JSON.parse('\x7B\x22h\x22\x3A\x7B\x22id\x22\x3A\x2281\x22...');
        # We need to extract the string inside JSON.parse('...') and decode it.
        
        patterns = {
            'rosterData': r"var rosterData\s*=\s*JSON\.parse\('([^']+)'\)",
            'matchInfo': r"var matchInfo\s*=\s*JSON\.parse\('([^']+)'\)"
        }
        
        # DEBUG: Find "rosterData" index
        idx = html.find("rosterData")
        if idx != -1:
            print(f"found 'rosterData' at index {idx}")
            print(f"Context: {html[idx:idx+100]}...")
        else:
            print("❌ 'rosterData' substring NOT found in HTML via requests.")

        data = {}
        
        for key, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                # The string is hex-escaped (e.g. \x7B). 
                # Python's codecs.decode can handle unicode_escape/hex.
                raw_str = match.group(1)
                try:
                    # Understat uses hex encoding like \x7B. 
                    # We can decode this.
                    decoded_str = codecs.decode(raw_str, 'unicode_escape')
                    json_data = json.loads(decoded_str)
                    data[key] = json_data
                    print(f"✅ Extracted {key}!")
                except Exception as e:
                    print(f"⚠️ Failed to decode {key}: {e}")
            else:
                print(f"❌ Could not find {key} pattern in HTML.")
                
        # Inspect Results
        if 'rosterData' in data:
            print("\n📊 Player xG Data Found:")
            # Roster data structure: {'h': {id: {player data}}, 'a': {id: {player data}}}
            # 'h' = Home, 'a' = Away
            
            for side in ['h', 'a']:
                team_data = data['rosterData'].get(side, {})
                print(f"  Team '{side}' ({len(team_data)} players):")
                
                # Print top 3 sorted by xG
                players = list(team_data.values())
                # xG is usually 'xG' key
                players.sort(key=lambda x: float(x.get('xG', 0)), reverse=True)
                
                for p in players[:3]:
                    print(f"    - {p['player']}: xG {p['xG']}, Goals {p['goals']}, Shots {p['shots']}")
                    
        return data

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    probe_understat()
