import requests
import re
from config.settings import Config
from utils.logging import log
from utils.team_names import normalize_team_name
from data.cache import cache_get, cache_set
from concurrent.futures import ThreadPoolExecutor, as_completed

def validate_action_network_auth():
    """
    Validate Action Network Cookie (Health Check).
    Raises Exception if invalid.
    """
    if not Config.ACTION_COOKIE:
        raise ValueError("ACTION_COOKIE is missing in .env")

    cookie_str = Config.ACTION_COOKIE.strip('"').strip("'")
    headers = {
        'authority': 'www.actionnetwork.com',
        'cookie': cookie_str,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    # 1. Get Build ID (Connectivity Check)
    try:
        home_res = requests.get('https://www.actionnetwork.com/', headers=headers, timeout=10)
        match = re.search(r'"buildId":"(.*?)"', home_res.text)
        if not match:
             raise ConnectionError("Could not retrieve buildId from Action Network homepage.")
        build_id = match.group(1)
    except Exception as e:
         raise ConnectionError(f"Action Network Connectivity Failed: {e}")

    # 2. Test Protected Endpoint
    test_url = f"https://www.actionnetwork.com/_next/data/{build_id}/nba/public-betting.json"
    
    res = requests.get(test_url, headers=headers, timeout=10)
    
    if res.status_code == 401 or res.status_code == 403:
        raise PermissionError("ACTION_COOKIE is Expired. Please update .env")
        
    if res.status_code != 200:
        log("WARN", f"Action Cookie Test returned {res.status_code} (Not 200/401). Proceeding with caution.")
        
    return True

def get_action_network_data():
    """
    Fetch Action Network public betting splits.
    """
    if not Config.ACTION_COOKIE:
        log("SHARP", "Action Network creds missing.")
        return {}

    # Cache Check (5 Min)
    cached = cache_get("action_network_data", ttl_seconds=300)
    if cached:
        log("SHARP", "✅ Using Cached Sharp Data")
        return cached

    log("SHARP", "Fetching Action Network Pro data (market-specific)...")

    cookie_str = Config.ACTION_COOKIE.strip('"').strip("'")
    headers = {
        'authority': 'www.actionnetwork.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'cookie': cookie_str,
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    # Step 1: Get buildId
    build_id = None
    try:
        home_res = requests.get('https://www.actionnetwork.com/', headers=headers, timeout=10)
        match = re.search(r'"buildId":"(.*?)"', home_res.text)
        if match:
            build_id = match.group(1)
        else:
            return {}
    except Exception:
        return {}

    if not build_id:
        return {}

    endpoints = {
        'NFL': 'public-betting.json',
        'NBA': 'nba/public-betting.json',
        'NCAAB': 'ncaab/public-betting.json',
        'NHL': 'nhl/public-betting.json',
        'SOCCER': 'soccer/public-betting.json',
        'UCL': 'soccer/champions-league/public-betting.json'
    }

    sharp_data = {}

    # Create Helper for Parallel Execution
    def _fetch_single_action_endpoint(suffix, b_id, hdrs):
        results = []
        target_url = f"https://www.actionnetwork.com/_next/data/{b_id}/{suffix}"
        
        try:
            res = requests.get(target_url, headers=hdrs, timeout=8)
            if res.status_code != 200:
                return []
                
            data = res.json()
            games = data.get('pageProps', {}).get('scoreboardResponse', {}).get('games', [])
            
            def _clean_pct(x):
                try: return float(x)
                except: return None

            for g in games:
                teams = g.get('teams', [])
                if not teams: continue
                
                team_map = {t.get('id'): t.get('full_name') for t in teams}
                home_id = g.get('home_team_id')
                away_id = g.get('away_team_id')
                
                home_name = team_map.get(home_id)
                away_name = team_map.get(away_id)
                
                if not home_name or not away_name: continue
                
                norm_h = normalize_team_name(home_name)
                norm_a = normalize_team_name(away_name)
                matchup_key = f"{norm_a} @ {norm_h}"
                
                markets = g.get('markets', {})
                if not markets: continue
                
                picked_event = None
                for _, book_data in markets.items():
                    ev = book_data.get('event', {})
                    if ev:
                        picked_event = ev
                        break
                if not picked_event: continue
                
                # SPREAD
                for outcome in picked_event.get('spread', []) or []:
                    tid = outcome.get('team_id')
                    tname = team_map.get(tid)
                    if not tname: continue
                    
                    bi = outcome.get('bet_info', {}) or {}
                    m = _clean_pct((bi.get('money', {}) or {}).get('percent'))
                    t = _clean_pct((bi.get('tickets', {}) or {}).get('percent'))
                    
                    results.append((matchup_key, "spread", normalize_team_name(tname), m, t))

                # MONEYLINE
                for outcome in picked_event.get('moneyline', []) or []:
                    tid = outcome.get('team_id')
                    tname = team_map.get(tid)
                    out_name = (outcome.get('name') or tname or "").strip()
                    
                    if out_name and ("draw" in out_name.lower() or "tie" in out_name.lower()):
                        side_key = "Draw"
                    else:
                        side_key = normalize_team_name(tname)
                    
                    if not side_key: continue
                    
                    bi = outcome.get('bet_info', {}) or {}
                    m = _clean_pct((bi.get('money', {}) or {}).get('percent'))
                    t = _clean_pct((bi.get('tickets', {}) or {}).get('percent'))
                    results.append((matchup_key, "moneyline", side_key, m, t))

                # TOTAL
                for outcome in picked_event.get('total', []) or []:
                    out_name = (outcome.get('name') or "").lower()
                    side = (outcome.get('side') or "").lower()
                    
                    side_key = None
                    if "over" in out_name or side in ("over", "o"): side_key = "Over"
                    elif "under" in out_name or side in ("under", "u"): side_key = "Under"
                    
                    if not side_key: continue
                    
                    bi = outcome.get('bet_info', {}) or {}
                    m = _clean_pct((bi.get('money', {}) or {}).get('percent'))
                    t = _clean_pct((bi.get('tickets', {}) or {}).get('percent'))
                    results.append((matchup_key, "total", side_key, m, t))
                    
        except Exception:
            pass
            
        return results

    # Main Parallel Execution
    all_splits = []
    log("SHARP", f"Fetching {len(endpoints)} sport endpoints in parallel...")
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {
            executor.submit(_fetch_single_action_endpoint, suffix, build_id, headers): sport 
            for sport, suffix in endpoints.items()
        }
        
        for future in as_completed(future_map):
            try:
                data = future.result()
                if data:
                    all_splits.extend(data)
            except Exception:
                pass

    # Aggregation
    for mk, mkt, sk, m_val, t_val in all_splits:
        if m_val is None or t_val is None: continue
        try:
            m_i = int(round(float(m_val)))
            t_i = int(round(float(t_val)))
            sharp_data.setdefault(mk, {}).setdefault(mkt, {})[sk] = {
                "money": m_i,
                "tickets": t_i
            }
        except:
            continue

    log("SHARP", f"Loaded market-specific sharp splits for {len(sharp_data)} matchups")
    
    # Cache Set
    if sharp_data:
        cache_set("action_network_data", sharp_data)
        
    return sharp_data
