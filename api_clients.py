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

                matchup_key = f"{away_name} @ {home_name}"

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
                    put_split(matchup_key, "spread", team_name, money_pct, ticket_pct)

                # Moneyline (team sides; draw/tie sometimes present)
                for outcome in picked_event.get('moneyline', []) or []:
                    tid = outcome.get('team_id')
                    team_name = team_map.get(tid)
                    out_name = (outcome.get('name') or team_name or "").strip()
                    if out_name and ("draw" in out_name.lower() or "tie" in out_name.lower()):
                        side_key = "Draw"
                    else:
                        side_key = team_name
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
                            p = p_res['response'][0]['predictions']['percent']
                            preds[mk] = {
                                'home_win': float(p['home'].strip('%')) / 100,
                                'draw': float(p['draw'].strip('%')) / 100,
                                'away_win': float(p['away'].strip('%')) / 100
                            }

                except:
                    continue

            if preds:
                break

    except:
        pass

    return preds
