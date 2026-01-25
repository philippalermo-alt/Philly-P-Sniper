
import requests
import json

def check_nhl_api():
    # 1. Get Schedule for a known date (Opening Night 2025)
    date_str = "2025-10-07"
    sched_url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    print(f"📅 Fetching Schedule: {sched_url}")
    
    try:
        res = requests.get(sched_url)
        data = res.json()
        
        # Find first game
        # Structure: output['gameWeek'][0]['games'][0]['id']
        
        game_id = None
        for day in data.get('gameWeek', []):
            if day['date'] == date_str:
                if day['games']:
                    game_id = day['games'][0]['id']
                    print(f"   Found Game ID: {game_id}")
                    break
        
        if not game_id:
            print("❌ No games found for date.")
            return

        # 2. Get Boxscore
        box_url = f"https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"
        print(f"📦 Fetching Boxscore: {box_url}")
        
        res_box = requests.get(box_url)
        box_data = res_box.json()
        
        # Check for officials
        # Usually checking keys
        # "gameOutcome", "boxscore", "officials"?
        
        # Let's inspect keys
        # print(f"   Keys: {list(box_data.keys())}")
        
        # Check specific known locations for officials
        # Often in 'summary' or separate 'officials' key? 
        # Actually in new API v1, it might be in `boxscore` -> `officials` isn't always there?
        # Let's dump first level keys and look for "summary" or "gameInfo".
        
        # Or just search the string dump for "Ref" or "Official"
        text_dump = json.dumps(box_data)
        if "official" in text_dump.lower() or "referee" in text_dump.lower():
             print("✅ 'Official' or 'Referee' found in JSON response!")
             # Try to extract
             # Some endpoints use 'gameBoxscore' > 'officials'
             # Or check `box_data` dict
             
             # Locate exact path
             import re
             matches = re.findall(r'.{0,50}referee.{0,50}', text_dump.lower())
             for m in matches[:3]:
                 print(f"   Match: ...{m}...")
                 
        else:
             print("❌ No 'official' data found in JSON.")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_nhl_api()
