import requests
import re
from datetime import datetime, timedelta
from config import Config
from utils import log

def get_action_network_data():
    """
    Fetch Action Network public betting splits and store them by matchup + market + side.

    Output shape:
      sharp_data["Away @ Home"]["moneyline"]["Team"] = {money:int, tickets:int}
      sharp_data["Away @ Home"]["spread"]["Team"]   = {money:int, tickets:int}
      sharp_data["Away @ Home"]["total"]["Over"]   = {money:int, tickets:int}
      sharp_data["Away @ Home"]["total"]["Under"]  = {money:int, tickets:int}

    Returns:
        dict: Sharp data organized by matchup, market, and side
    """
    if not Config.ACTION_COOKIE:
        log("SHARP", "Action Network creds missing.")
        return {}

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

    def normalize_pct(x):
        try:
            x = float(x)
        except (TypeError, ValueError):
            return None
        return x  # Assume Action Network always returns 0-100 scale now

    def put_split(matchup_key, market_key, side_key, money_pct, ticket_pct):
        if money_pct is None or ticket_pct is None:
            return
        try:
            m_i = int(round(float(money_pct)))
            t_i = int(round(float(ticket_pct)))
        except Exception:
            return
        sharp_data.setdefault(matchup_key, {}).setdefault(market_key, {})[side_key] = {
            "money": m_i,
            "tickets": t_i,
        }

    for sport, suffix in endpoints.items():
        target_url = f"https://www.actionnetwork.com/_next/data/{build_id}/{suffix}"
        try:
            res = requests.get(target_url, headers=headers, timeout=6)
            if res.status_code != 200:
                continue

            data = res.json()
            games = data.get('pageProps', {}).get('scoreboardResponse', {}).get('games', [])
            if not games:
                continue

            for g in games:
                teams = g.get('teams', [])
                if not teams:
                    continue

                team_map = {t.get('id'): t.get('full_name') for t in teams}

                home_id = g.get('home_team_id')
                away_id = g.get('away_team_id')

                home_name = team_map.get(home_id)
                away_name = team_map.get(away_id)

                if not home_name or not away_name:
                    continue

                from utils import normalize_team_name
                norm_h = normalize_team_name(home_name)
                norm_a = normalize_team_name(away_name)
                matchup_key = f"{norm_a} @ {norm_h}"

                markets = g.get('markets', {})
                if not markets:
                    continue

                picked_event = None
                for _, book_data in markets.items():
                    ev = book_data.get('event', {})
                    if ev:
                        picked_event = ev
                        break
                if not picked_event:
                    continue

                # Spread (team sides)
                for outcome in picked_event.get('spread', []) or []:
                    tid = outcome.get('team_id')
                    team_name = team_map.get(tid)
                    if not team_name:
                        continue
                    bi = outcome.get('bet_info', {}) or {}
                    money_pct = normalize_pct((bi.get('money', {}) or {}).get('percent'))
                    ticket_pct = normalize_pct((bi.get('tickets', {}) or {}).get('percent'))
                    
                    from utils import normalize_team_name
                    put_split(matchup_key, "spread", normalize_team_name(team_name), money_pct, ticket_pct)

                # Moneyline (team sides; draw/tie sometimes present)
                for outcome in picked_event.get('moneyline', []) or []:
                    tid = outcome.get('team_id')
                    team_name = team_map.get(tid)
                    out_name = (outcome.get('name') or team_name or "").strip()
                    if out_name and ("draw" in out_name.lower() or "tie" in out_name.lower()):
                        side_key = "Draw"
                    else:
                        from utils import normalize_team_name
                        side_key = normalize_team_name(team_name)
                    if not side_key:
                        continue
                    bi = outcome.get('bet_info', {}) or {}
                    money_pct = normalize_pct((bi.get('money', {}) or {}).get('percent'))
                    ticket_pct = normalize_pct((bi.get('tickets', {}) or {}).get('percent'))
                    put_split(matchup_key, "moneyline", side_key, money_pct, ticket_pct)

                # Total (Over/Under)
                for outcome in picked_event.get('total', []) or []:
                    out_name = (outcome.get('name') or "").lower()
                    side = (outcome.get('side') or "").lower()
                    side_key = None
                    if "over" in out_name or side in ("over", "o"):
                        side_key = "Over"
                    elif "under" in out_name or side in ("under", "u"):
                        side_key = "Under"
                    if not side_key:
                        continue
                    bi = outcome.get('bet_info', {}) or {}
                    money_pct = normalize_pct((bi.get('money', {}) or {}).get('percent'))
                    ticket_pct = normalize_pct((bi.get('tickets', {}) or {}).get('percent'))
                    put_split(matchup_key, "total", side_key, money_pct, ticket_pct)

        except Exception:
            continue

    log("SHARP", f"Loaded market-specific sharp splits for {len(sharp_data)} matchups")
    return sharp_data

def get_soccer_predictions(league_key):
    """
    Fetch soccer match predictions from Football API.

    Args:
        league_key: Soccer league identifier

    Returns:
        dict: Predictions keyed by matchup string (Away @ Home)
    """
    lid = Config.SOCCER_LEAGUE_IDS.get(league_key)
    if not lid:
        return {}

    preds = {}

    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        for season in [2025, 2024]:
            for date in [today, tomorrow]:
                url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&date={date}"
                headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}

                try:
                    res = requests.get(url, headers=headers, timeout=10).json()
                    if res.get('results', 0) == 0:
                        continue

                    for f in res.get('response', []):
                        mk = f"{f['teams']['away']['name']} @ {f['teams']['home']['name']}"
                        if mk in preds:
                            continue

                        p_res = requests.get(
                            f"https://v3.football.api-sports.io/predictions?fixture={f['fixture']['id']}",
                            headers=headers,
                            timeout=10
                        ).json()

                        if p_res.get('results', 0) > 0:
                            pred_data = p_res['response'][0]['predictions']
                            p = pred_data['percent']
                            goals = pred_data.get('goals', {})
                            
                            # Parse goals (often string "-1.5" or "1.5")
                            h_goals = abs(float(goals.get('home', 0))) if goals.get('home') else 1.2
                            a_goals = abs(float(goals.get('away', 0))) if goals.get('away') else 1.0
                            
                            preds[mk] = {
                                'home_win': float(p['home'].strip('%')) / 100,
                                'draw': float(p['draw'].strip('%')) / 100,
                                'away_win': float(p['away'].strip('%')) / 100,
                                'home_goals': h_goals,
                                'away_goals': a_goals
                            }

                except:
                    continue

            if preds:
                break

    except:
        pass

    return preds


def get_nhl_player_stats(season=20242025):
    """
    Fetches NHL player stats (Shots on Goal) from the official NHL Stats API.
    Bypasses API-Sports which lacks this data.
    
    URL: https://api.nhle.com/stats/rest/en/skater/summary
    """
    log("PROPS", "Fetching NHL player stats from Official NHL API...")
    
    # Season format for NHL API is '20242025'
    # API-Sports sends '2024', so we ensure it's formatted correctly
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
                # Clean name (remove accents if needed, but Odds API usually has them)
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

def fetch_espn_scores(sport_keys, specific_date=None):
    """
    Fetch live scores from ESPN's public hidden API (Free).
    Used for both Dashboard Live Scores and Bet Grading.
    
    Args:
        sport_keys (list): List of sport/league keys (e.g. ['NBA', 'NFL'])
        specific_date (str, optional): Date in 'YYYYMMDD' format. If None, checks today + yesterday.
        
    Returns:
        list: List of game dictionaries
    """
    import pytz
    
    games = []
    unique_sports = set(sport_keys)
    
    # Map internal keys to ESPN API paths (support list of paths)
    # Format: {sport}/{league}
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
            'soccer/eng.1',          # EPL
            'soccer/eng.2',          # Championship
            'soccer/uefa.champions', # UCL
            'soccer/uefa.europa',    # Europa
            'soccer/esp.1',          # La Liga
            'soccer/ger.1',          # Bundesliga
            'soccer/ita.1',          # Serie A
            'soccer/fra.1',          # Ligue 1
            'soccer/usa.1',          # MLS
            'soccer/fifa.friendly'   # Friendlies
        ],
        'CHAMPIONS': ['soccer/uefa.champions'],
        'LALIGA': ['soccer/esp.1'],
        'BUNDESLIGA': ['soccer/ger.1'],
        'SERIEA': ['soccer/ita.1'],
        'LIGUE1': ['soccer/fra.1']
    }

    processed_paths = set()

    if specific_date:
        dates_to_check = [specific_date]
    else:
        # FORCE US/EASTERN DATE logic for grading relevancy
        tz = pytz.timezone('US/Eastern')
        now_et = datetime.now(tz)
        
        # Check Today and Yesterday to catch late night games finished past midnight UTC
        dates_to_check = [now_et.strftime('%Y%m%d'), (now_et - timedelta(days=1)).strftime('%Y%m%d')]

    for date_str in dates_to_check:
        for sport_key in unique_sports:
            paths = ESPN_MAP.get(sport_key, [])
            # Support single string fallback if needed, but we standardized to list above
            if isinstance(paths, str):
                paths = [paths]
                
            for espn_path in paths:
                # Avoid duplicate calls if multiple keys map to same path
                path_date_key = f"{espn_path}_{date_str}"
                if path_date_key in processed_paths:
                    continue
                processed_paths.add(path_date_key)

                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={date_str}"
                    
                    # Use User-Agent to avoid generic bot blocking
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    }
                    
                    r = requests.get(url, headers=headers, timeout=5)
                    
                    if r.status_code == 200:
                        res = r.json()
                        events = res.get('events', [])
                        
                        for event in events:
                            # ESPN structure: events -> competitions[0] -> competitors
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
                            
                            games.append({
                                'id': event['id'],
                                'sport_key': sport_key,
                                'sport': sport_key,
                                'home': h_name,
                                'away': a_name,
                                'home_score': h_score,
                                'away_score': a_score,
                                'status': status_detail,
                                'is_complete': is_complete,
                                'score_text': f"{status_detail}: {a_name} {a_score} - {h_name} {h_score}",
                                'commence': event.get('date') # ISO string
                            })

                except Exception as e:
                    log("WARN", f"ESPN fetch failed for {espn_path}: {e}")
                    continue
                
    return games

def get_nba_refs():
    """
    Scrape official NBA referee assignments from official.nba.com.
    Returns:
        list: List of dicts {'Game': 'Team A @ Team B', 'Crew Chief': str, 'Referee': str, 'Umpire': str}
    """
    from bs4 import BeautifulSoup
    
    url = "https://official.nba.com/referee-assignments/"
    
    # Robust headers to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/'
    }
    
    log("REFS", f"Fetching NBA Referee Data from {url}...")
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            log("WARN", f"Failed to fetch refs: {res.status_code}")
            return []
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Finding the main table
        table = soup.find('table', class_='table')
        
        if not table:
            log("WARN", "No table found with class='table' on ref page.")
            return []
            
        assignments = []
        
        # Iterate Rows (skip header)
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if not cols:
                continue # Header row or empty
                
            # Expected columns: Game, Crew Chief, Referee, Umpire, Alternate
            # Game is text "Team A @ Team B"
            game_str = cols[0].get_text(strip=True)
            
            def clean_ref(cell):
                text = cell.get_text(strip=True)
                # Remove (Number) e.g. "Scott Foster (#48)" -> "Scott Foster"
                if "(" in text:
                    text = text.split("(")[0].strip()
                return text

            chief = clean_ref(cols[1])
            ref = clean_ref(cols[2])
            umpire = clean_ref(cols[3])
            
            if game_str and chief:
                assignments.append({
                    'Game': game_str,
                    'Crew Chief': chief,
                    'Referee': ref,
                    'Umpire': umpire
                })
                
        log("REFS", f"Found {len(assignments)} referee assignments.")
        return assignments

    except Exception as e:
        log("ERROR", f"Error scraping refs: {e}")
        return []
