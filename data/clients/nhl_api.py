import requests
from utils.logging import log

def get_nhl_player_stats(season=20242025):
    """
    Fetches NHL player stats (Shots on Goal) from the official NHL Stats API.
    """
    log("PROPS", "Fetching NHL player stats from Official NHL API...")
    
    if isinstance(season, int) and season < 10000:
        season = f"{season}{season+1}"
    
    url = f"https://api.nhle.com/stats/rest/en/skater/summary?isAggregate=false&isGame=false&sort=[{{%22property%22:%22points%22,%22direction%22:%22DESC%22}}]&start=0&limit=-1&cayenneExp=seasonId={season}%20and%20gameTypeId=2"
    
    try:
        res = requests.get(url, timeout=15).json()
        if 'data' not in res:
            log("ERROR", "NHL API returned unexpected format")
            return {}

        player_db = {}
        for p in res['data']:
            name = p.get('skaterFullName')
            games = p.get('gamesPlayed')
            shots = p.get('shots')
            team = p.get('teamAbbrev')
            
            if name and games and games > 0 and shots is not None:
                avg_sog = shots / games
                player_db[name] = {
                    'team': team,
                    'games': games,
                    'total_shots': shots,
                    'avg_shots': avg_sog
                }

        log("PROPS", f"Loaded stats for {len(player_db)} NHL players")
        return player_db

    except Exception as e:
        log("ERROR", f"Failed to fetch NHL stats: {e}")
        return {}
