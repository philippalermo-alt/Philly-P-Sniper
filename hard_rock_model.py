# (full file contents)
import os, requests, psycopg2, json, numpy as np, pandas as pd

from datetime import datetime, timedelta, timezone

from scipy import stats

from io import StringIO

import difflib

import time

import re



# One-time debug counters for calculate_match_stats TypeErrors
_calc_stats_typeerror_count = 0
_calc_stats_typeerror_max = 5



class Config:

    ODDS_API_KEY = os.getenv('ODDS_API_KEY', '7e6462d56d833b4f0102707ad16661e6')

    KENPOM_API_KEY = os.getenv('KENPOM_API_KEY', '766ca6d4909eb92ac05730e493d85a342ada30d6f44fc84e086da3da6137815f')

    FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY', '46af6649182657150c97bf25cae9220a')

    ACTION_COOKIE = os.getenv('ACTION_COOKIE')

    DATABASE_URL = os.getenv('DATABASE_URL')

    

    BANKROLL = 451.16

    KELLY_FRAC = 0.125

    MAX_STAKE_PCT = 0.06

    

    MIN_EDGE = 0.00

    MAX_EDGE = 0.50

    MAX_PROBABILITY = 0.72

    

    MARKET_WEIGHT_US = 0.15

    MARKET_WEIGHT_SOCCER = 0.80

    

    DEBUG_MODE = True

    

    PREFERRED_BOOKS = ['hardrockbet', 'draftkings', 'fanduel', 'betmgm', 'caesars', 'bovada']

    MAIN_MARKETS = 'h2h,spreads,totals'

    EXOTIC_MARKETS = 'h2h_h1,spreads_h1,totals_h1'



    NBA_MARGIN_STD = 11.0    

    NCAAB_MARGIN_STD = 9.5   

    NFL_MARGIN_STD = 13.0    

    NHL_MARGIN_STD = 1.8



    LEAGUES = [

        'basketball_nba', 'basketball_ncaab', 'americanfootball_nfl', 'icehockey_nhl',

        'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga', 

        'soccer_france_ligue_one', 'soccer_italy_serie_a', 'soccer_germany_bundesliga2',

        'soccer_efl_champ'

    ]

    

    SOCCER_LEAGUE_IDS = {

        'soccer_epl': 39, 'soccer_spain_la_liga': 140, 'soccer_germany_bundesliga': 78,

        'soccer_france_ligue_one': 61, 'soccer_italy_serie_a': 135,

        'soccer_germany_bundesliga2': 79, 'soccer_efl_champ': 40

    }



def log(step, message):

    if Config.DEBUG_MODE:

        print(f"🔄 [{step}] {message}")



def get_db():

    try: return psycopg2.connect(Config.DATABASE_URL, sslmode='prefer')

    except Exception as e:

        print(f"❌ [DB ERROR] {e}")

        return None



def init_db():

    log("DB", "Initializing database schema...")

    conn = get_db()

    if not conn: return

    cur = conn.cursor()

    try:

        cur.execute('''CREATE TABLE IF NOT EXISTS intelligence_log (

            event_id TEXT PRIMARY KEY, 

            timestamp TIMESTAMP, 

            kickoff TIMESTAMP,

            sport TEXT, 

            teams TEXT, 

            selection TEXT, 

            odds REAL, 

            true_prob REAL, 

            edge REAL, 

            stake REAL,

            outcome TEXT DEFAULT 'PENDING', 

            user_bet BOOLEAN DEFAULT FALSE,

            closing_odds REAL,

            ticket_pct INTEGER,

            money_pct INTEGER,

            trigger_type TEXT

        )''')

        # Check if column exists before trying to ALTER (avoids locking if not needed)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='sharp_score'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS sharp_score INTEGER")
        
        # Add user_odds and user_stake columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='user_odds'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS user_odds REAL")

        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='user_stake'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS user_stake REAL")
            
        # Create Settings Table
        cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
        # Insert default bankroll if not exists
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', '451.16') ON CONFLICT (key) DO NOTHING")
            
        conn.commit()

    except Exception as e: 

        print(f"❌ [DB INIT] {e}")

        conn.rollback()

    finally: 

        cur.close()

        conn.close()



# ---------- Helpers ----------

def _to_python_scalar(v):
    """
    Convert numpy scalar types to native Python types so psycopg2 won't end up
    with representations like 'np.float64(...)' when queries fail or are logged.
    """
    try:
        if isinstance(v, (np.generic,)):
            return v.item()
    except Exception:
        pass
    return v


def safe_execute(cur, sql, params=None):
    """
    Execute a parameterized SQL statement while:
    - coercing numpy scalars to native Python types
    - rolling back the current transaction on error so subsequent statements can run
    """
    try:
        if params is None:
            return cur.execute(sql)
        normalized = tuple(_to_python_scalar(p) for p in params)
        return cur.execute(sql, normalized)
    except Exception as e:
        try:
            print(f"❌ [DB ERROR] {e}")
            cur.connection.rollback()
        except Exception:
            pass
        return None


def _num(v, default=0.0):
    """
    Safely convert v to a float if possible, otherwise return default.
    Use this to avoid None values ending up in arithmetic/division.
    """
    if v is None:
        return float(default)
    try:
        return float(v)
    except Exception:
        try:
            if isinstance(v, (np.generic,)):
                return float(v.item())
        except Exception:
            pass
    return float(default)
# -----------------------------



def get_calibration(sport):

    conn = get_db()

    if not conn: return 1.0

    try:

        cur = conn.cursor()

        cur.execute("SELECT true_prob, outcome FROM intelligence_log WHERE sport = %s AND outcome IN ('WON', 'LOST')", (sport,))

        rows = cur.fetchall()

        cur.close()

        conn.close()

        if len(rows) < 10: return 1.0

        predicted = sum(r[0] for r in rows) / len(rows)

        actual = sum(1 for r in rows if r[1] == 'WON') / len(rows)

        if predicted == 0: return 1.0

        return max(0.85, min(actual / predicted, 1.15))

    except: return 1.0



def grade_bet(selection, home_team, away_team, home_score, away_score, period_scores=None):
    """
    Grades wagers with specific support for 1st Half (1H) markets and team name cleaning.
    """
    # 🧹 STEP 1: Identify if this is a 1H bet
    is_1h = any(term in selection for term in ["1H", "1st Half", "Halftime"])
    
    # 🧹 STEP 2: Use period scores for 1H bets if they exist in the API response
    # This prevents using the Final score (e.g. 30-35) for a 1H bet (e.g. 20-10)
    if is_1h and period_scores:
        try:
            # Look for scores labeled '1' or '1st Half' in the API period list
            h_1h = next((p['score'] for p in period_scores if p['name'] == home_team and '1' in p.get('description', '')), None)
            a_1h = next((p['score'] for p in period_scores if p['name'] == away_team and '1' in p.get('description', '')), None)
            
            if h_1h is not None and a_1h is not None:
                home_score, away_score = int(h_1h), int(a_1h)
        except:
            pass # Fall back to provided scores if period extraction fails

    margin = home_score - away_score

    # 1. Moneyline
    if " ML" in selection:
        # Clean the name: Remove "1H", "1st Half", "ML", then trim and lowercase
        pick = selection.replace(" ML", "").replace("1H", "").replace("1st Half", "").strip().lower()
        
        # Fuzzy match logic (similar to dashboard)
        pick_matches_home = pick in home_team.lower() or home_team.lower() in pick
        pick_matches_away = pick in away_team.lower() or away_team.lower() in pick
        
        if margin > 0 and pick_matches_home: return 'WON'
        if margin < 0 and pick_matches_away: return 'WON'
        if margin == 0: return 'PUSH'
        return 'LOST'

    # 2. Soccer Draws
    if selection == "Draw ML":
        return 'WON' if margin == 0 else 'LOST'

    # 3. Spreads
    if ('+' in selection or '-' in selection) and '(' not in selection:
        try:
            parts = selection.rsplit(' ', 1)
            raw_team, spread = parts[0].strip(), float(parts[1])
            
            # Clean the team name so "Purdue 1H" matches "Purdue"
            clean_team = raw_team.replace("1H", "").replace("1st Half", "").strip().lower()
            
            # Fuzzy match for spreads too
            matches_home = clean_team in home_team.lower() or home_team.lower() in clean_team
            matches_away = clean_team in away_team.lower() or away_team.lower() in clean_team
            
            if matches_home:
                cov = margin + spread
            elif matches_away:
                cov = -margin + spread
            else:
                return 'PENDING' # Safety: Name still doesn't match

            if cov > 0: return 'WON'
            if cov < 0: return 'LOST'
            return 'PUSH'
        except: pass

    # 4. Over/Under
    if "Over" in selection or "Under" in selection:
        try:
            line = float(selection.split()[-1])
            total = home_score + away_score
            if "Over" in selection: 
                return 'WON' if total > line else 'LOST'
            if "Under" in selection: 
                return 'WON' if total < line else 'LOST'
        except: pass

    return 'PENDING'



def settle_pending_bets():
    log("GRADING", "Checking for pending bets to settle...")
    conn = get_db()
    if not conn: return
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")
    pending_count = cur.fetchone()[0]
    log("GRADING", f"Found {pending_count} past-due bets waiting for scores.")

    conn = get_db()

    if not conn: return

    cur = conn.cursor()

    try:

        cur.execute("SELECT event_id, sport, selection FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")

        pending = cur.fetchall()

        if not pending: return

        sport_map = {
            'NBA': 'basketball_nba', 
            'NCAAB': 'basketball_ncaab', 
            'NFL': 'americanfootball_nfl', 
            'NHL': 'icehockey_nhl', 
            'EPL': 'soccer_epl', 
            'LALIGA': 'soccer_spain_la_liga',
            'CHAMP': 'soccer_efl_champ',
            'MLB': 'baseball_mlb',
            'SOCCER': 'soccer_epl' # Default fallback
        }

        graded = 0

        for sport in set([p[1] for p in pending]):

            league = sport_map.get(sport)

            if not league: continue

            try:

                url = f"https://api.the-odds-api.com/v4/sports/{league}/scores/?apiKey={Config.ODDS_API_KEY}&daysFrom=3"

                res = requests.get(url, timeout=10).json()

                if not isinstance(res, list): continue

                for game in res:

                    if not game.get('completed') or not game.get('scores'): continue

                    scores = {s['name']: int(s['score']) for s in game['scores']}

                    home, away = game['home_team'], game['away_team']

                    if home not in scores or away not in scores: continue

                    for event_id, _, selection in pending:

                        if event_id.startswith(game['id']): 

                            # Pass game['scores'] to enable 1H grading logic
                            outcome = grade_bet(selection, home, away, scores[home], scores[away], game['scores'])

                            if outcome:
                                safe_execute(cur, "UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, event_id))
                                graded += 1

            except: pass

        conn.commit()

        if graded > 0: log("GRADING", f"Graded {graded} bets")

    except: pass

    finally: cur.close(); conn.close()



def get_action_network_data():
    """Fetch Action Network public betting splits and store them by matchup + market + side.

    Output shape:
      sharp_data["Away @ Home"]["moneyline"]["Team"] = {money:int, tickets:int}
      sharp_data["Away @ Home"]["spread"]["Team"]   = {money:int, tickets:int}
      sharp_data["Away @ Home"]["total"]["Over"]   = {money:int, tickets:int}
      sharp_data["Away @ Home"]["total"]["Under"]  = {money:int, tickets:int}
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
        'SOCCER': 'soccer/public-betting.json'
    }

    sharp_data = {}

    def normalize_pct(x):
        try:
            x = float(x)
        except (TypeError, ValueError):
            return None
        return x # Assume Action Network always returns 0-100 scale now

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

                # team_id -> full name
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

                # pick first book that has an event block
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

    lid = Config.SOCCER_LEAGUE_IDS.get(league_key)

    if not lid: return {}

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

                    if res.get('results', 0) == 0: continue

                    for f in res.get('response', []):

                        mk = f"{f['teams']['away']['name']} @ {f['teams']['home']['name']}"

                        if mk in preds: continue

                        p_res = requests.get(f"https://v3.football.api-sports.io/predictions?fixture={f['fixture']['id']}", headers=headers, timeout=10).json()

                        if p_res.get('results', 0) > 0:

                            p = p_res['response'][0]['predictions']['percent']

                            preds[mk] = {'home_win': float(p['home'].strip('%'))/100, 'draw': float(p['draw'].strip('%'))/100, 'away_win': float(p['away'].strip('%'))/100}

                except: continue

            if preds: break

    except: pass

    return preds



def get_team_ratings():

    log("RATINGS", "Fetching KenPom, NBA, NHL, and NFL data...")

    ratings = {}

    headers = {'User-Agent': 'Mozilla/5.0'}



    # --- NFL ---

    try:

        off_ypp = pd.read_html(StringIO(requests.get("https://www.teamrankings.com/nfl/stat/yards-per-play", headers=headers).text))[0]

        def_ypp = pd.read_html(StringIO(requests.get("https://www.teamrankings.com/nfl/stat/opponent-yards-per-play", headers=headers).text))[0]

        off_ppg = pd.read_html(StringIO(requests.get("https://www.teamrankings.com/nfl/stat/points-per-game", headers=headers).text))[0]

        def_ppg = pd.read_html(StringIO(requests.get("https://www.teamrankings.com/nfl/stat/opponent-points-per-game", headers=headers).text))[0]

        

        for _, row in off_ypp.iterrows():

            team = str(row['Team']); ratings[team] = {'sport': 'NFL'}

            ratings[team]['off_ypp'] = float(row['2024'])

        for _, row in def_ypp.iterrows():

            if str(row['Team']) in ratings: ratings[str(row['Team'])]['def_ypp'] = float(row['2024'])

        for _, row in off_ppg.iterrows():

            if str(row['Team']) in ratings: ratings[str(row['Team'])]['off_ppg'] = float(row['2024'])

        for _, row in def_ppg.iterrows():

            if str(row['Team']) in ratings: ratings[str(row['Team'])]['def_ppg'] = float(row['2024'])

        log("RATINGS", f"Loaded NFL ratings for {len([k for k,v in ratings.items() if v.get('sport')=='NFL'])} teams")

    except: pass



    # --- NHL ---

    try:

        nhl_headers = {'x-apisports-key': Config.FOOTBALL_API_KEY} 

        leagues = requests.get("https://v1.hockey.api-sports.io/leagues?name=NHL", headers=nhl_headers, timeout=10).json()

        nhl_id = 57 

        if leagues.get('results', 0) > 0: nhl_id = leagues['response'][0]['id']

        url = f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season=2025"

        res = requests.get(url, headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) == 0:

            url = f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season=2024"

            res = requests.get(url, headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) > 0:

            flattened = [item for sublist in res['response'] for item in sublist]

            total_goals = 0; total_games = 0

            for row in flattened:

                try:

                    gp = row['games']['played']; gf = row['goals']['for']

                    if gp > 0: total_goals += _num(gf, 0); total_games += _num(gp, 0)

                except: pass

            avg_goals = (total_goals / total_games) if total_games > 0 else 3.0

            for row in flattened:

                try:

                    name = row['team']['name']; gp = row['games']['played']

                    if _num(gp, 0) < 5: continue 

                    gf_avg = _num(row['goals']['for'], 0) / _num(gp, 1); ga_avg = _num(row['goals']['against'], 0) / _num(gp, 1)

                    ratings[name] = {'attack': gf_avg/avg_goals, 'defense': ga_avg/avg_goals, 'league_avg_goals': avg_goals, 'sport': 'NHL'}

                except: pass

            log("RATINGS", f"Loaded {len([r for r in ratings.values() if r['sport']=='NHL'])} NHL ratings")

    except Exception as e: print(f"   ⚠️ NHL fetch failed: {e}")



    # --- NCAAB ---

    try:

        kp_headers = {'Authorization': f'Bearer {Config.KENPOM_API_KEY}'}

        raw_ratings = requests.get("https://kenpom.com/api.php?endpoint=ratings&y=2026", headers=kp_headers, timeout=10).json()

        for t in raw_ratings:

            ratings[t['TeamName']] = {'offensive_eff': float(t['AdjOE']), 'defensive_eff': float(t['AdjDE']), 'tempo': float(t['AdjTempo']), 'sport': 'NCAAB'}

        log("RATINGS", f"Loaded {len(raw_ratings)} KenPom ratings")

    except Exception as e: print(f"   ⚠️ KenPom error: {e}")

    

    # --- NBA ---

    try:
        url = 'https://www.teamrankings.com/nba/stat/offensive-efficiency'
        nba_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        df = pd.read_html(StringIO(requests.get(url, headers=nba_headers, timeout=10).text))[0]

        col = next((c for c in df.columns if '2024' in str(c) or '2025' in str(c) or 'Last' in str(c)), None)

        if col:

            for _, row in df.iterrows():

                val = float(str(row[col]).replace('%', ''))

                if val < 20.0: val = val * 100

                ratings[str(row['Team'])] = {'offensive_eff': val, 'defensive_eff': 110.0, 'tempo': 100.0, 'sport': 'NBA'}

            log("RATINGS", "Loaded NBA ratings")

    except Exception as e: print(f"   ⚠️ NBA error: {e}")

    

    return ratings



def calculate_match_stats(home, away, ratings, target_sport):
    """
    Defensive implementation that logs and returns None tuple on TypeError.
    Uses _num() to coerce None / numpy scalars to numeric defaults.
    Also performs a one-time detailed debug log for the first few TypeErrors.
    """
    global _calc_stats_typeerror_count, _calc_stats_typeerror_max

    home_r = ratings.get(home)
    if not home_r:
        m = difflib.get_close_matches(home, ratings.keys(), n=1, cutoff=0.75)
        if m: home_r = ratings[m[0]]

    away_r = ratings.get(away)
    if not away_r:
        m = difflib.get_close_matches(away, ratings.keys(), n=1, cutoff=0.75)
        if m: away_r = ratings[m[0]]

    if not home_r:
        home_r = {'offensive_eff': 110.0, 'defensive_eff': 110.0, 'tempo': 70.0,
                  'sport': target_sport, 'league_avg_goals': 3.0, 'attack': 1.0, 'defense': 1.0}
    if not away_r:
        away_r = {'offensive_eff': 110.0, 'defensive_eff': 110.0, 'tempo': 70.0,
                  'sport': target_sport, 'league_avg_goals': 3.0, 'attack': 1.0, 'defense': 1.0}

    if home_r.get('sport') != target_sport:
        return None, None, None, None
    sport = target_sport

    try:
        if sport == 'NFL':
            h_off_ypp = _num(home_r.get('off_ypp'), 5.0); h_def_ypp = _num(home_r.get('def_ypp'), 5.0)
            a_off_ypp = _num(away_r.get('off_ypp'), 5.0); a_def_ypp = _num(away_r.get('def_ypp'), 5.0)
            home_net = h_off_ypp - h_def_ypp; away_net = a_off_ypp - a_def_ypp
            margin = ((home_net - away_net) * 4.5) + 2.0

            h_off_ppg = _num(home_r.get('off_ppg'), 20.0); h_def_ppg = _num(home_r.get('def_ppg'), 20.0)
            a_off_ppg = _num(away_r.get('off_ppg'), 20.0); a_def_ppg = _num(away_r.get('def_ppg'), 20.0)
            home_proj = (h_off_ppg + a_def_ppg) / 2; away_proj = (a_off_ppg + h_def_ppg) / 2
            total = home_proj + away_proj
            return margin, total, Config.NFL_MARGIN_STD, sport

        if sport == 'NHL':
            avg_goals = _num(home_r.get('league_avg_goals'), 3.0)
            home_att = _num(home_r.get('attack'), 1.0); home_def = _num(home_r.get('defense'), 1.0)
            away_att = _num(away_r.get('attack'), 1.0); away_def = _num(away_r.get('defense'), 1.0)
            home_exp = home_att * away_def * avg_goals
            away_exp = away_att * home_def * avg_goals
            home_exp += 0.2
            return (home_exp - away_exp), (home_exp + away_exp), Config.NHL_MARGIN_STD, sport

        avg_tempo = (_num(home_r.get('tempo'), 70.0) + _num(away_r.get('tempo'), 70.0)) / 2
        poss = avg_tempo / 100
        baseline = 118.0 if sport == 'NBA' else 105.0
        home_exp_pts = (_num(home_r.get('offensive_eff'), baseline) - (_num(away_r.get('defensive_eff'), baseline) - baseline)) * poss
        away_exp_pts = (_num(away_r.get('offensive_eff'), baseline) - (_num(home_r.get('defensive_eff'), baseline) - baseline)) * poss

        home_court = 3.5 if sport == 'NCAAB' else 2.5
        margin = (home_exp_pts - away_exp_pts) + home_court
        total = home_exp_pts + away_exp_pts
        std = Config.NCAAB_MARGIN_STD if sport == 'NCAAB' else Config.NBA_MARGIN_STD
        return margin, total, std, sport

    except TypeError as e:
        # One-time detailed debug log for first few occurrences
        _calc_stats_typeerror_count += 1
        if _calc_stats_typeerror_count <= _calc_stats_typeerror_max:
            log("ERROR", f"calculate_match_stats TypeError #{_calc_stats_typeerror_count} for {home} vs {away} ({sport}): {e}")
            try:
                log("ERROR", f"home_r keys: {list(home_r.keys())}, away_r keys: {list(away_r.keys())}")
                # sample some values
                sample_info = {
                    'home_off': home_r.get('offensive_eff'),
                    'home_def': home_r.get('defensive_eff'),
                    'home_tempo': home_r.get('tempo'),
                    'away_off': away_r.get('offensive_eff'),
                    'away_def': away_r.get('defensive_eff'),
                    'away_tempo': away_r.get('tempo'),
                }
                log("ERROR", f"sample values: {sample_info}")
            except Exception:
                pass
        else:
            # After max, log succinctly to avoid spam
            log("ERROR", f"calculate_match_stats TypeError for {home} vs {away} ({sport}); further details suppressed.")
        return None, None, None, None
    except Exception as e:
        log("ERROR", f"calculate_match_stats unexpected error for {home} vs {away} ({sport}): {e}")
        return None, None, None, None



def calculate_kelly_stake(edge, decimal_odds):

    if edge <= 0: return 0.0

    b = decimal_odds - 1

    p = (edge + 1) / decimal_odds

    q = 1 - p

    f_star = (b * p - q) / b

    stake = f_star * Config.KELLY_FRAC * Config.BANKROLL

    max_stake = Config.BANKROLL * Config.MAX_STAKE_PCT

    return min(stake, max_stake)



def process_markets(match, ratings, calibration, cur, all_opps, target_sport, seen_matches, sharp_data, is_soccer=False, predictions=None):
    now_utc = datetime.now(timezone.utc)
    mdt = datetime.fromisoformat(match['commence_time'].replace('Z', '+00:00'))
    if mdt < now_utc: return 

    bookie = next((b for b in match.get('bookmakers', []) if b['key'] in Config.PREFERRED_BOOKS), None)
    if not bookie: return

    home, away = match['home_team'], match['away_team']
    match_id = f"{home} vs {away}"
    if match_id in seen_matches: return
    seen_matches.add(match_id)# MATCH SHARP DATA (market-specific)
    def _sharp_score_from_split(money_pct, ticket_pct):
        try:
            m_val = float(money_pct)
            t_val = float(ticket_pct)
        except Exception:
            return 0
        gap = m_val - t_val
        gap_score = max(0, min(1, (gap - 5) / 25))
        minority_score = max(0, min(1, (55 - t_val) / 25))
        money_majority_score = max(0, min(1, (m_val - 50) / 20))
        return int(round(100 * (0.55 * gap_score + 0.25 * minority_score + 0.20 * money_majority_score)))

    # Fuzzy-match the matchup key ONCE per game, then look up splits by market+side
    match_key = f"{away} @ {home}"
    matched_key = None
    m_match = difflib.get_close_matches(match_key, sharp_data.keys(), n=1, cutoff=0.6) if sharp_data else []
    if m_match:
        matched_key = m_match[0]

    def get_sharp_split(market_key, side_key):
        if not matched_key:
            return None, None, 0
        split = sharp_data.get(matched_key, {}).get(market_key, {}).get(side_key)
        if not split:
            return None, None, 0
        m_pct = split.get("money")
        t_pct = split.get("tickets")
        return m_pct, t_pct, _sharp_score_from_split(m_pct, t_pct)

    # --- SOCCER ---
    if is_soccer:
        mk = f"{away} @ {home}"
        pred = predictions.get(mk) if predictions else None

        if not pred and predictions:
            for pk, pd in predictions.items():
                try:
                    pa, ph = pk.split(" @ ")
                except Exception:
                    continue
                if (difflib.SequenceMatcher(None, home, ph).ratio() > 0.6 and
                    difflib.SequenceMatcher(None, away, pa).ratio() > 0.6):
                    pred = pd
                    break

        if not pred:
            # no prediction available; skip soccer processing for this event
            pred = None

        if pred:
            soccer_match_opps = []
            for m in bookie['markets']:
                if m['key'] != 'h2h':
                    continue
                for o in m.get('outcomes', []):
                    name = o['name']
                    price = o.get('price')
                    if price is None or price == 0:
                        # defensive: skip outcomes with missing/zero price
                        continue

                    if name == home:
                        mp = pred['home_win']
                        sel = f"{home} ML"
                    elif name == away:
                        mp = pred['away_win']
                        sel = f"{away} ML"
                    elif 'Draw' in name or 'Tie' in name:
                        mp = pred['draw']
                        sel = "Draw ML"
                    else:
                        continue

                    mp *= calibration
                    mp = min(mp, Config.MAX_PROBABILITY)

                    tp = (Config.MARKET_WEIGHT_SOCCER * (1 / price)) + ((1 - Config.MARKET_WEIGHT_SOCCER) * mp)
                    edge = (tp * price) - 1

                    if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                        stake = calculate_kelly_stake(edge, price)
                        soccer_match_opps.append({
                            'Date': mdt.strftime('%Y-%m-%d'),
                            'Kickoff': match['commence_time'],
                            'Sport': 'SOCCER',
                            'Event': mk,
                            'Selection': sel,
                            'True_Prob': tp,
                            'Target': 1 / tp if tp else 0,
                            'Dec_Odds': price,
                            'Edge_Val': edge,
                            'Edge': f"{edge*100:.1f}%",
                            'Stake': f"${stake:.2f}"
                        })

            if soccer_match_opps:
                best_opp = sorted(soccer_match_opps, key=lambda x: x['Edge_Val'], reverse=True)[0]
                all_opps.append(best_opp)
                if cur:
                    try:
                        unique_id = f"{match['id']}_{best_opp['Selection'].replace(' ', '_')}"
                        sql = """
                            INSERT INTO intelligence_log 
                            (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score) 
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) 
                            ON CONFLICT (event_id) DO UPDATE SET 
                                odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                                stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                                closing_odds=EXCLUDED.closing_odds, ticket_pct=EXCLUDED.ticket_pct, money_pct=EXCLUDED.money_pct, sharp_score=EXCLUDED.sharp_score;
                        """

                        # Pull market-specific sharp split for this soccer selection
                        side_key = None
                        if best_opp['Selection'].startswith(home):
                            side_key = home
                        elif best_opp['Selection'].startswith(away):
                            side_key = away
                        elif best_opp['Selection'].startswith("Draw"):
                            side_key = "Draw"
                        m_val, t_val, sharp_score_val = (None, None, 0)
                        if side_key:
                            m_val, t_val, sharp_score_val = get_sharp_split("moneyline", side_key)
                        params = (
                            unique_id, datetime.now(), best_opp['Kickoff'], 'SOCCER', best_opp['Event'], 
                            best_opp['Selection'], float(best_opp['Dec_Odds']), float(best_opp['True_Prob']), 
                            float(best_opp['Edge_Val']), float(best_opp['Stake'].replace('$','')), 'model', float(best_opp['Dec_Odds']),
                            int(t_val) if t_val is not None else None,
                            int(m_val) if m_val is not None else None,
                            int(sharp_score_val)
                        )
                        safe_execute(cur, sql, params)
                    except Exception as e:
                        print(f"❌ [DB ERROR] Failed to save {best_opp['Event']}: {e}")
        # end soccer processing

        # IMPORTANT: do not fall through into US sports logic for soccer matches
        return

    # --- US SPORTS ---
    exp_margin, exp_total, margin_std, sport = calculate_match_stats(home, away, ratings, target_sport)
    if exp_margin is None: return

    for m in bookie['markets']:
        key = m['key']
        if any(x in key for x in ['alternate', 'team', 'q1', 'q2', 'q3', 'q4', '_h2']): continue
        
        for o in m.get('outcomes', []):
            name, price, point = o['name'], o.get('price'), o.get('point', 0)
            if price is None or price == 0:
                # defensive: skip outcomes with missing/zero price
                continue

            mp, sel = None, None
            
            if 'spreads' in key:
                eff_m, eff_s = exp_margin, margin_std
                lbl = "1H" if 'h1' in key else ""
                if lbl: eff_m *= 0.48; eff_s *= 0.75
                sel = f"{name} {lbl} {point:+.1f}".strip()
                mp = 1 - stats.norm.cdf((-point - (eff_m if name == home else -eff_m)) / eff_s)
            elif 'h2h' in key:
                eff_m, eff_s = exp_margin, margin_std
                lbl = "1H" if 'h1' in key else ""
                if lbl: eff_m *= 0.48; eff_s *= 0.75
                sel = f"{name} {lbl} ML".strip()
                mp = 1 - stats.norm.cdf((0 - (eff_m if name == home else -eff_m)) / eff_s)
            elif 'totals' in key:
                eff_t, std_mult = exp_total, (1.8 if sport == 'NBA' else 1.6 if sport == 'NCAAB' else 1.2)
                eff_s = margin_std * std_mult
                lbl = "1H" if 'h1' in key else ""
                if lbl: eff_t = exp_total * 0.50; eff_s = margin_std * 0.75 * std_mult
                if name == 'Over':
                    sel = f"{lbl} Over {point}".strip(); mp = 1 - stats.norm.cdf((point - eff_t) / eff_s)
                else:
                    sel = f"{lbl} Under {point}".strip(); mp = stats.norm.cdf((point - eff_t) / eff_s)
            
            if mp:
                mp *= calibration
                mp = min(mp, Config.MAX_PROBABILITY)
                # price is already validated above
                tp = (Config.MARKET_WEIGHT_US * (1/price)) + ((1 - Config.MARKET_WEIGHT_US) * mp)
                edge = ((tp * price) - 1) * (0.75 if sport == 'NHL' else 1.0)
                
                if Config.MIN_EDGE <= edge < Config.MAX_EDGE:
                    stake = calculate_kelly_stake(edge, price)
                    opp = {
                        'Date': mdt.strftime('%Y-%m-%d'), 'Kickoff': match['commence_time'], 'Sport': sport, 'Event': f"{away} @ {home}",
                        'Selection': sel, 'True_Prob': tp, 'Target': 1/tp if tp else 0, 'Dec_Odds': price,
                        'Edge_Val': edge, 'Edge': f"{edge*100:.1f}%", 'Stake': f"${stake:.2f}"
                    }
                    all_opps.append(opp)
                    if cur:
                        try:
                            unique_id = f"{match['id']}_{sel.replace(' ', '_')}"

                            # Pull market-specific sharp split for this wager
                            sharp_market = None
                            sharp_side = None
                            if 'spreads' in key:
                                sharp_market = "spread"
                                sharp_side = name
                            elif 'h2h' in key:
                                sharp_market = "moneyline"
                                sharp_side = "Draw" if ('draw' in str(name).lower() or 'tie' in str(name).lower()) else name
                            elif 'totals' in key:
                                sharp_market = "total"
                                sharp_side = "Over" if str(name).lower() == "over" else "Under"
                            
                            m_val, t_val, sharp_score_val = (None, None, 0)
                            if sharp_market and sharp_side:
                                m_val, t_val, sharp_score_val = get_sharp_split(sharp_market, sharp_side)
                            sql = """
                                INSERT INTO intelligence_log 
                                (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score) 
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) 
                                ON CONFLICT (event_id) DO UPDATE SET 
                                    odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                                    stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                                    closing_odds=EXCLUDED.closing_odds, ticket_pct=EXCLUDED.ticket_pct, money_pct=EXCLUDED.money_pct, sharp_score=EXCLUDED.sharp_score;
                            """
                            params = (
                                unique_id, datetime.now(), opp['Kickoff'], sport, opp['Event'], 
                                opp['Selection'], float(price), float(tp), float(edge), float(stake), 'model', float(price),
                                int(t_val) if t_val is not None else None,
                            int(m_val) if m_val is not None else None,
                            int(sharp_score_val)
                            )
                            safe_execute(cur, sql, params)
                        except Exception as e: print(f"❌ [DB ERROR] Failed to save {opp['Event']}: {e}")

        # end for markets

    # end process_markets



def run_sniper():

    log("INIT", "Starting Philly P Sniper...")

    init_db()

    settle_pending_bets()

    ratings = get_team_ratings()

    sharp_data = get_action_network_data()

    conn = get_db()

    cur = conn.cursor() if conn else None

    all_opps = []

    

    now_utc = datetime.now(timezone.utc)

    limit_time = now_utc + timedelta(hours=72)

    log("TIME", f"Window: {now_utc.strftime('%Y-%m-%d %H:%M')} UTC to {limit_time.strftime('%Y-%m-%d %H:%M')} UTC")

    

    for league in Config.LEAGUES:

        sport_key = league.split('_')[-1].upper()

        target_sport = 'NBA' if 'nba' in league else 'NCAAB' if 'ncaab' in league else 'NFL' if 'nfl' in league else 'NHL'

        

        calibration = get_calibration(target_sport)

        log("SCAN", f"Scanning {sport_key} ({league})... Calibration: {calibration:.2f}x")

        

        preds = get_soccer_predictions(league) if 'soccer' in league else {}

        try:

            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.MAIN_MARKETS}"

            res = requests.get(url, timeout=15).json()

            if not isinstance(res, list): continue

            matches = []

            for m in res:

                mdt = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00'))

                if mdt > limit_time: continue 

                matches.append(m)

            log("SCAN", f"Found {len(matches)} matches")

            seen_matches = set()
            for m in matches:

                process_markets(m, ratings, calibration, cur, all_opps, target_sport, seen_matches, sharp_data, is_soccer=('soccer' in league), predictions=preds)

                if sport_key in ['NBA', 'NFL', 'NCAAB']:

                    try:

                        url = f"https://api.the-odds-api.com/v4/sports/{league}/events/{m['id']}/odds?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.EXOTIC_MARKETS}"

                        deep = requests.get(url, timeout=10).json()

                        if 'id' in deep: process_markets(deep, ratings, calibration, cur, all_opps, target_sport, seen_matches, sharp_data, is_soccer=False)

                    except: pass

        except Exception as e: log("ERROR", f"Failed {league}: {e}")



    if cur: conn.commit(); conn.close()

    

    print(f"\n✅ Scan complete. Found {len(all_opps)} valid bets.")

    if all_opps:

        pd.set_option('display.max_rows', None)

        df = pd.DataFrame(all_opps)

        final_picks = []

        for sport in df['Sport'].unique():

            sport_df = df[df['Sport'] == sport].sort_values(by='Edge_Val', ascending=False)

            final_picks.extend(sport_df.head(3).to_dict('records'))

        if len(final_picks) < 15:

            existing_ids = {f"{p['Event']}{p['Selection']}" for p in final_picks}

            remaining = df[~df.apply(lambda x: f"{x['Event']}{x['Selection']}" in existing_ids, axis=1)]

            final_picks.extend(remaining.sort_values(by='Edge_Val', ascending=False).head(15 - len(final_picks)).to_dict('records'))

        top_15 = pd.DataFrame(final_picks).sort_values(by='Edge_Val', ascending=False).head(15)

        all_bets = df.sort_values(by='Edge_Val', ascending=False)

        cols = ['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'True_Prob', 'Target', 'Dec_Odds', 'Edge', 'Stake']

        print("\n" + "="*60)

        print("🎯 [TOP 15 PICKS] (Diversity Enforced)")

        print("="*60)

        print(top_15[cols].to_string(index=False))

        print("\n" + "="*60)

        print("📜 [ALL RECOMMENDED BETS]")

        print("="*60)

        print(all_bets[cols].to_string(index=False))



if __name__ == "__main__":

    run_sniper()
