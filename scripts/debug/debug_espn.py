import requests
import json

def get_espn_scores(sport_path, date_str=None):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport_path}/scoreboard"
    if date_str:
        url += f"?dates={date_str}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        print(f"Fetching: {url}")
        res = requests.get(url, headers=headers, timeout=5).json()
        games = []
        for event in res.get('events', []):
            comp = event['competitions'][0]
            status = event['status']['type']['shortDetail']
            
            home = next((c for c in comp['competitors'] if c['homeAway'] == 'home'), {})
            away = next((c for c in comp['competitors'] if c['homeAway'] == 'away'), {})
            
            h_team = home.get('team', {}).get('displayName', 'Unknown')
            a_team = away.get('team', {}).get('displayName', 'Unknown')
            h_score = home.get('score', '0')
            a_score = away.get('score', '0')
            
            games.append(f"{status} [{event['date']}]: {a_team} vs {h_team} ({a_score}-{h_score})")
        return games
    except Exception as e:
        return [f"Error: {e}"]

# print("--- NBA ---")
# print(get_espn_scores("basketball/nba"))

# print("--- NBA ---")
# print(get_espn_scores("basketball/nba"))

print("\n--- NHL (Jan 19) ---")
print(get_espn_scores("hockey/nhl", "20260119"))

print("\n--- NHL (Jan 20) ---")
print(get_espn_scores("hockey/nhl", "20260120"))

# print("\n--- NCAAB ---")
# print(get_espn_scores("basketball/mens-college-basketball"))
