
import requests
import re
import json
import html

def test_understat():
    url = "https://understat.com/league/EPL"
    print(f"🌍 Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"❌ Failed: {resp.status_code}")
            return
            
        # Understat stores data in a script tag:
        # var teamsData = JSON.parse('...');
        
        match = re.search(r"var teamsData = JSON.parse\('([^']+)'\)", resp.text)
        if match:
            # The JSON inside is hex-encoded sometimes or just escaped?
            # Understat usually uses standard JSON but inside a string.
            # Example: JSON.parse('\x7B\x22id\x22\x3A\x2282\x22...')
            
            raw_data = match.group(1)
            # It might be hex encoded. Python's string-escape might handle it?
            # Actually, encoding to bytes and decoding 'unicode_escape' works for \xHH
            decoded_data = raw_data.encode('utf-8').decode('unicode_escape')
            
            data = json.loads(decoded_data)
            
            print("✅ Successfully found and parsed Team Data!")
            print(f"   Teams Found: {len(data)}")
            
            # Print Top 3 by xG (Understat keys are usually 'xG', 'title')
            # Data structure is typically a dictionary of id -> team_obj
            # or a list.
            
            # Let's peek at one
            sample_id = list(data.keys())[0]
            team = data[sample_id]
            print(f"   Sample: {team['title']} (xG: {team['history'][-1]['xG']})")
            
        else:
            print("❌ Could not find 'teamsData' in page source.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_understat()
