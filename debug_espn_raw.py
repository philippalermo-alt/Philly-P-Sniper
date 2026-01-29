import requests
import json

def test_url(url, name):
    print(f"Testing {name}: {url}")
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = r.json()
        events = data.get('events', [])
        print(f"  -> Found {len(events)} events.")
        if len(events) > 0:
            print(f"  -> First Event: {events[0]['shortName']}")
    except Exception as e:
        print(f"  -> Error: {e}")

def main():
    date = "20260125" # Sunday
    
    # 1. Current Logic (Groups=50, limit=1000)
    u1 = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={date}&groups=50&limit=1000"
    test_url(u1, "Groups=50 + Limit=1000")
    
    # 2. No Groups (All games)
    u2 = f"https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={date}&limit=1000"
    test_url(u2, "No Groups + Limit=1000")
    
    # 3. NBA Check
    u3 = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={date}&limit=1000"
    test_url(u3, "NBA Standard")

if __name__ == "__main__":
    main()
