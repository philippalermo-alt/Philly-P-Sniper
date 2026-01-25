from datetime import datetime, timedelta
from config.settings import Config
from utils.logging import log
from data.cache import cache_get, cache_set
from data.clients.base import BaseAPIClient

class OddsAPIClient(BaseAPIClient):
    def __init__(self):
        super().__init__("https://api.the-odds-api.com/v4")
        self.api_key = Config.ODDS_API_KEY

    def get_events(self, sport_key: str):
        """Fetch upcoming events for a sport."""
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'commenceTimeFrom': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'commenceTimeTo': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        return self.get(f"sports/{sport_key}/events", params=params)

    def get_event_odds(self, sport_key: str, event_id: str, markets: str):
        """Fetch specific markets for an event."""
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': markets,
            'oddsFormat': 'american'
        }
        return self.get(f"sports/{sport_key}/events/{event_id}/odds", params=params)

def fetch_prop_odds(sport_key, markets="player_goal_scorer_anytime"):
    """
    Fetch player prop odds from The-Odds-API (Paid Tier).
    Wrapper to maintain backward compatibility using OddsAPIClient.
    """
    if not Config.ODDS_API_KEY:
        log("WARN", "No ODDS_API_KEY found.")
        return {}
        
    # Cache Check (2 Mins)
    cache_key = f"prop_odds_{sport_key}_{markets}"
    cached = cache_get(cache_key, ttl_seconds=120)
    if cached:
        log("PROPS", f"Using Cached Props for {sport_key}")
        return cached
        
    client = OddsAPIClient()
    
    # 1. Get Events
    events = client.get_events(sport_key)
    if not events or not isinstance(events, list):
        log("ERROR", f"Odds API Events Error: {events}")
        return {}
        
    prop_data = {}
    
    for event in events:
        event_id = event['id']
        teams = f"{event['home_team']} vs {event['away_team']}"
        
        # 2. Get Odds per Event
        odds_res = client.get_event_odds(sport_key, event_id, markets)
        if not odds_res:
            continue
            
        bookmakers = odds_res.get('bookmakers', [])
        
        for book in bookmakers:
            book_id = book['key']
            if book_id not in ['draftkings', 'fanduel', 'betmgm', 'caesars']:
                continue # Filter for main books
                
            for market in book.get('markets', []):
                m_key = market['key']
                for outcome in market.get('outcomes', []):
                    p_name = outcome.get('description') # Player Name
                    if not p_name: continue
                    
                    price = outcome['price']
                    point = outcome.get('point')
                    
                    if p_name not in prop_data: prop_data[p_name] = {}
                    if m_key not in prop_data[p_name]: prop_data[p_name][m_key] = []
                    
                    prop_data[p_name][m_key].append({
                        'book': book_id,
                        'price': price,
                        'line': point,
                        'game': teams
                    })
                    
    log("PROPS", f"Fetched live odds for {len(prop_data)} players in {sport_key}")
    
    if prop_data:
        cache_set(cache_key, prop_data)
        
    return prop_data
