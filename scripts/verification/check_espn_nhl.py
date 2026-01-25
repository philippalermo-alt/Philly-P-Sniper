
import requests
import json

def check_espn_refs():
    # 1. Get Scoreboard to find a Game ID
    # Date: Oct 7, 2025 (Season Opener)
    date_str = "20251007" 
    scoreboard_url = f"http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard?dates={date_str}"
    
    print(f"📅 Fetching ESPN Scoreboard: {scoreboard_url}")
    try:
        res = requests.get(scoreboard_url)
        data = res.json()
        
        events = data.get('events', [])
        if not events:
            print("❌ No events found.")
            return

        game_id = events[0]['id']
        name = events[0]['name']
        print(f"   Found Game: {name} (ID: {game_id})")
        
        # 2. Get Game Summary (Boxscore)
        summary_url = f"http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary?event={game_id}"
        print(f"📦 Fetching Summary: {summary_url}")
        
        s_res = requests.get(summary_url)
        s_data = s_res.json()
        
        # Inspect for officials
        # Usually in gameInfo -> officials
        
        game_info = s_data.get('gameInfo', {})
        officials = game_info.get('officials', [])
        
        if officials:
            print(f"✅ Found Officials in gameInfo:")
            print(json.dumps(officials, indent=2))
        else:
            print("❌ No 'officials' in gameInfo.")
            
            # Search whole JSON text for "referee"
            text = json.dumps(s_data)
            if "referee" in text.lower() or "official" in text.lower():
                print("⚠️ 'referee' or 'official' found somewhere in JSON (extracted snippet):")
                import re
                matches = re.findall(r'.{0,50}(?:referee|official).{0,50}', text.lower())
                for m in matches[:3]:
                    print(f"   Match: ...{m}...")
            else:
                print("❌ 'referee' keyword not found in entire response.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_espn_refs()
