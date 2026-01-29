import requests
import logging
import unicodedata
from datetime import datetime
from config import Config
from utils import match_team

# Setup Logger
logger = logging.getLogger("LineupClient")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

def normalize_name(name):
    """
    Robust name normalization:
    - Lowercase
    - Remove accents (é -> e)
    - Remove punctuation
    """
    if not name: return ""
    # Normalize unicode characters (e.g., Mbappé -> Mbappe)
    n = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower().replace('.', '').replace('-', ' ').strip()

def get_confirmed_lineup(league_key, home_team, away_team):
    """
    Fetch confirmed Starting XI for a match using API-Football.
    
    Args:
        league_key (str): Odds API league key (e.g. 'soccer_epl')
        home_team (str): Home team name
        away_team (str): Away team name
        
    Returns:
        set: Normalized names of starting players.
        OR
        None: If lineups are not yet released, match not found, or API fail.
    """
    # 1. Get League ID
    lid = Config.SOCCER_LEAGUE_IDS.get(league_key)
    if not lid:
        # Fallback mapping if not in config
        if 'epl' in league_key: lid = 39
        elif 'la_liga' in league_key: lid = 140
        elif 'bundesliga' in league_key: lid = 78
        elif 'serie_a' in league_key: lid = 135
        elif 'ligue_one' in league_key: lid = 61
        else:
            return None 

    headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
    if not Config.FOOTBALL_API_KEY:
        logger.warning("No FOOTBALL_API_KEY found.")
        return None

    try:
        # 2. Find Fixture ID
        # Search by league AND date (Today)
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Optimization: API-Football allows searching by team? No, finding all fixtures for league/date is cheap (1 call)
        url_fixtures = f"https://v3.football.api-sports.io/fixtures?league={lid}&season=2025&date={date_str}"
        # Fallback to 2024 season if 2025 empty? (Depending on current season logic)
        # Try 2024 if current date logic suggests it?
        # Actually, let's try the primary season loop logic or just checking response.
        
        # We try 2025 first (Current for 2026 Sim?)
        # Wait, Sim Date is Jan 24, 2026. So Season is 2025-2026. Season Key is 2025.
        
        # DEBUG: Print Search Info
        print(f"DEBUG_LC: Searching LeagueID={lid} for '{home_team}' vs '{away_team}'", flush=True)

        r = requests.get(url_fixtures, headers=headers, timeout=10)
        data = r.json()
        
        items = data.get('response', [])
        print(f"DEBUG_LC: Found {len(items)} fixtures for date {date_str} league {lid}", flush=True)
        
        fixture_id = None
        for f in items:
            teams = f['teams']
            # print(f"   🐛 [DEBUG-LC] Found Fixture: {teams['home']['name']} vs {teams['away']['name']}", flush=True)
            h_name = teams['home']['name']
            a_name = teams['away']['name']
            
            # Fuzzy Match
            m_h = match_team(home_team, [h_name])
            m_a = match_team(away_team, [a_name])
            
            # print(f"   Candidate: {h_name} v {a_name} -> MatchH={m_h} MatchA={m_a}", flush=True)

            # Strict Match Required
            if m_h and m_a:
                print(f"✅ DEBUG_LC: MATCH FOUND! {h_name} ({m_h}) vs {a_name} ({m_a})", flush=True)
                fixture_id = f['fixture']['id']
                break
            
            # Swap Check
            m_h_swap = match_team(home_team, [a_name])
            m_a_swap = match_team(away_team, [h_name])
            if m_h_swap and m_a_swap:
                print(f"✅ DEBUG_LC: SWAP MATCH FOUND! {a_name} ({m_h_swap}) vs {h_name} ({m_a_swap})", flush=True)
                fixture_id = f['fixture']['id']
                break
                
        if not fixture_id:
            logger.info(f"LineupClient: Fixture not found on API-Football for {home_team} vs {away_team} (League {lid})")
            return None
            
        # 3. Get Lineups
        print(f"DEBUG_LC: Fetching Lineups for Fixture {fixture_id}", flush=True)
        url_lineups = f"https://v3.football.api-sports.io/fixtures/lineups?fixture={fixture_id}"
        r_l = requests.get(url_lineups, headers=headers, timeout=10)
        l_data = r_l.json()
        
        if l_data.get('results', 0) == 0:
            logger.info(f"LineupClient: Lineups not released for Fixture {fixture_id}")
            return None
            
        starters = set()
        for team_data in l_data['response']:
            # team_data has 'team' and 'startXI'
            for player_wrapper in team_data.get('startXI', []):
                p = player_wrapper.get('player', {})
                p_name = p.get('name')
                if p_name:
                    starters.add(normalize_name(p_name))
                    
        return starters

    except Exception as e:
        logger.error(f"LineupClient API Error: {e}")
        return None

if __name__ == "__main__":
    # Test
    print("Testing Lineup Fetch (API-Football)...")
    # Simulation: Ensure you have key env var set if running locally
    pass
