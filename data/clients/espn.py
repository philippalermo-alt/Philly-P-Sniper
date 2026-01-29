import requests
import pytz
from datetime import datetime, timedelta
from utils.logging import log
from data.cache import cache_get, cache_set
from concurrent.futures import ThreadPoolExecutor, as_completed

def _fetch_single_espn_path(espn_path, date_str):
    """
    Helper for parallel ESPN fetch.
    Returns list of formatted games or empty list.
    """
    u = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={date_str}&limit=1000"
    
    # Special handling for NCAAB to get all Div I games (groups=50) -> Removed to get ALL games
    if 'mens-college-basketball' in espn_path:
        u += "&groups=50" 

    url = u
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            res = r.json()
            events = res.get('events', [])
            return (espn_path, events)
            
    except Exception as e:
        log("WARN", f"ESPN fetch failed for {espn_path}: {e}")
        
    return (espn_path, [])

def fetch_espn_scores(sport_keys, specific_date=None):
    """
    Fetch live scores from ESPN's public hidden API (Free).
    Used for both Dashboard Live Scores and Bet Grading.
    PARALLELIZED VERSION.
    """
    
    # Cache Check (45s - very short for live scores, but avoids double hitting in quick refreshes)
    # Key must depend on sports + date
    cache_key = f"espn_scores_{'-'.join(sorted(sport_keys))}_{specific_date or 'default'}"
    cached = cache_get(cache_key, ttl_seconds=60)
    if cached:
        return cached

    games = []
    unique_sports = set(sport_keys)
    
    # Map internal keys to ESPN API paths (support list of paths)
    ESPN_MAP = {
        'basketball_nba': ['basketball/nba'],
        'NBA': ['basketball/nba'],
        'basketball_ncaab': ['basketball/mens-college-basketball'],
        'NCAAB': ['basketball/mens-college-basketball'],
        'icehockey_nhl': ['hockey/nhl'],
        'NHL': ['hockey/nhl'],
        'americanfootball_nfl': ['football/nfl'],
        'NFL': ['football/nfl'],
        'baseball_mlb': ['baseball/mlb'],
        'MLB': ['baseball/mlb'],
        'soccer_epl': ['soccer/eng.1'],
        'SOCCER': [
            'soccer/eng.1',
            'soccer/esp.1',
            'soccer/ger.1',
            'soccer/ita.1',
            'soccer/fra.1',
            'soccer/ned.1',
            'soccer/por.1',
            'soccer/uefa.champions',
            'soccer/uefa.europa',
            'soccer/eng.2',
            'soccer/usa.1',
            'soccer/fifa.friendly'
        ],
        'CHAMPIONS': ['soccer/uefa.champions'],
        'LALIGA': ['soccer/esp.1'],
        'BUNDESLIGA': ['soccer/ger.1'],
        'SERIEA': ['soccer/ita.1'],
        'LIGUE1': ['soccer/fra.1']
    }

    processed_paths = set()
    tasks = [] # List of (espn_path, date_str, sport_keys_that_use_this_path)

    if specific_date:
        dates_to_check = [specific_date]
    else:
        tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(tz)
        dates_to_check = [
            now_et.strftime('%Y%m%d'), 
            (now_et - timedelta(days=1)).strftime('%Y%m%d'),
            (now_et - timedelta(days=2)).strftime('%Y%m%d'),
            (now_et - timedelta(days=3)).strftime('%Y%m%d'),
            (now_et - timedelta(days=4)).strftime('%Y%m%d')
        ]

    # 1. Build Task List (Deduplicated)
    # We need to map paths back to sport_keys during processing
    path_to_sport_map = {} # path -> list of sport_keys
    
    for sport_key in unique_sports:
        paths = ESPN_MAP.get(sport_key, [])
        if isinstance(paths, str): paths = [paths]
        
        for p in paths:
            if p not in path_to_sport_map:
                path_to_sport_map[p] = []
            path_to_sport_map[p].append(sport_key)

            for d in dates_to_check:
                task_key = f"{p}_{d}"
                if task_key not in processed_paths:
                    processed_paths.add(task_key)
                    tasks.append((p, d))
    
    if not tasks:
        return []

    log("ESPN", f"Fetching {len(tasks)} endpoints in parallel...")
    
    # 2. Execute Parallel Fetch
    # Max workers = 10 to avoid blasting ESPN too hard, but faster than serial.
    fetched_results = []
    
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_map = {executor.submit(_fetch_single_espn_path, p, d): (p, d) for p, d in tasks}
        
        for future in as_completed(future_map):
            p, d = future_map[future]
            try:
                # Returns (path, events_list)
                path_ret, events = future.result()
                if events:
                    fetched_results.append((path_ret, events))
            except Exception as e:
                log("WARN", f"Parallel Fetch Exception for {p}: {e}")

    # 3. Process Results (CPU Bound - fast enough)
    count = 0
    for path, events in fetched_results:
        # Determine sport_key(s) associated with this path
        # Let's use the first one from our map.
        associated_keys = path_to_sport_map.get(path, ['UNKNOWN'])
        primary_sport = associated_keys[0]

        for event in events:
            # Safe parsing
            try:
                comp = event['competitions'][0]
                status_detail = event.get('status', {}).get('type', {}).get('shortDetail', 'Scheduled')
                is_complete = event.get('status', {}).get('type', {}).get('completed', False)
                
                # Teams
                competitors = comp.get('competitors', [])
                home_comp = next((c for c in competitors if c['homeAway'] == 'home'), {})
                away_comp = next((c for c in competitors if c['homeAway'] == 'away'), {})
                
                h_name = home_comp.get('team', {}).get('displayName', 'Home')
                a_name = away_comp.get('team', {}).get('displayName', 'Away')
                h_score = int(home_comp.get('score', 0))
                a_score = int(away_comp.get('score', 0))
                
                venue = comp.get('venue', {}).get('fullName', 'Unknown Arena')
                neutral_site = comp.get('neutralSite', False)
                notes = [n.get('headline') for n in event.get('notes', []) if n.get('headline')]
                
                # Linescores (Period Scores)
                h_linescores = [float(x.get('value', 0)) for x in home_comp.get('linescores', [])]
                a_linescores = [float(x.get('value', 0)) for x in away_comp.get('linescores', [])]
                
                # Odds
                odds_info = {}
                if 'odds' in comp and comp['odds']:
                    try:
                        main_odds = comp['odds'][0]
                        odds_info = {
                            'overUnder': main_odds.get('overUnder'),
                            'spread': main_odds.get('details')
                        }
                    except:
                        pass
                
                games.append({
                    'id': event['id'],
                    'sport_key': primary_sport, # Assign primary
                    'sport': primary_sport,
                    'home': h_name,
                    'away': a_name,
                    'home_score': h_score,
                    'away_score': a_score,
                    'home_linescores': h_linescores,
                    'away_linescores': a_linescores,
                    'status': status_detail,
                    'is_complete': is_complete,
                    'score_text': f"{status_detail}: {a_name} {a_score} - {h_name} {h_score}",
                    'commence': event.get('date'),
                    'venue': venue,
                    'neutral_site': neutral_site,
                    'notes': notes,
                    'odds': odds_info
                })
                count += 1
            except Exception:
                pass
                
    log("ESPN", f"Processed {count} games from parallel fetch.")
    
    if games:
        cache_set(cache_key, games)
        
    return games
