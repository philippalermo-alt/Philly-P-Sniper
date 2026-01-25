
import requests
from datetime import datetime
import pytz

def test_fetch():
    # Simulate the dashboard logic
    keys = ['basketball_ncaab', 'NBA', 'NCAAB', 'icehockey_nhl']
    
    ESPN_MAP = {
        'basketball_nba': 'basketball/nba',
        'NBA': 'basketball/nba',
        'basketball_ncaab': 'basketball/mens-college-basketball',
        'NCAAB': 'basketball/mens-college-basketball',
        'icehockey_nhl': 'hockey/nhl',
        'NHL': 'hockey/nhl'
    }
    
    tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz)
    date_str = now_et.strftime('%Y%m%d')
    print(f"📅 Date used: {date_str} (Time: {now_et.strftime('%H:%M:%S')})")
    
    processed_paths = set()
    
    for sport_key in keys:
        espn_path = ESPN_MAP.get(sport_key)
        if not espn_path or espn_path in processed_paths:
            continue
        processed_paths.add(espn_path)
        
        base_url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={date_str}"
        if 'college-basketball' in espn_path:
            base_url += "&groups=50&limit=900"
            
        print(f"\n🔗 Fetching: {base_url}")
        
        try:
            r = requests.get(base_url, timeout=5)
            if r.status_code == 200:
                res = r.json()
                events = res.get('events', [])
                print(f"✅ Found {len(events)} events.")
                
                # Print first few to check names
                for i, event in enumerate(events[:5]):
                    short_name = event.get('shortName', 'Unknown')
                    status = event.get('status', {}).get('type', {}).get('shortDetail', 'Sched')
                    
                    comp = event['competitions'][0]
                    competitors = comp.get('competitors', [])
                    h = next((c for c in competitors if c['homeAway'] == 'home'), {})
                    a = next((c for c in competitors if c['homeAway'] == 'away'), {})
                    
                    h_name = h.get('team', {}).get('displayName')
                    a_name = a.get('team', {}).get('displayName')
                    
                    print(f"   [{i+1}] {status}: {a_name} vs {h_name}")
            else:
                print(f"❌ Status Code: {r.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_fetch()
