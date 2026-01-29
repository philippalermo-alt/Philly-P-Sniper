import requests
import pandas as pd
from io import StringIO
from datetime import datetime
from config.settings import Config
from utils.logging import log
from utils.math import _num
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_current_seasons():
    """Dynamically determine current season years based on date."""
    now = datetime.now()
    month = now.month
    year = now.year
    
    # NFL: Season starts Sept (9), ends Feb (2).
    nfl_season = year - 1 if month < 3 else year
    
    # NCAAB/NBA/NHL: Spans two years (e.g., 2025-2026).
    kenpom_year = year if month > 6 else year
    if month > 6:
        kenpom_year = year + 1
    else:
        kenpom_year = year
        
    return str(nfl_season), str(kenpom_year)

def _fetch_nfl_ratings(year, headers):
    """Fetch NFL Ratings from TeamRankings."""
    ratings = {}
    try:
        base_url = "https://www.teamrankings.com/nfl/stat"
        
        # Helper inner function for sequential fetches within NFL thread
        def fetch_tr(metric, stat_name):
            try:
                res = requests.get(f"{base_url}/{metric}", headers=headers, timeout=5)
                df = pd.read_html(StringIO(res.text))[0]
                col = next((c for c in df.columns if year in str(c)), 'Last 3')
                
                for _, row in df.iterrows():
                    team = str(row['Team'])
                    if team not in ratings: ratings[team] = {'sport': 'NFL'}
                    ratings[team][stat_name] = float(row[col])
            except Exception as e:
                log("WARN", f"Failed to fetch NFL {stat_name}: {e}")

        fetch_tr("yards-per-play", "off_ypp")
        fetch_tr("opponent-yards-per-play", "def_ypp")
        fetch_tr("points-per-game", "off_ppg")
        fetch_tr("opponent-points-per-game", "def_ppg")
        
        return ratings
    except Exception as e:
        log("ERROR", f"NFL Ratings failed: {e}")
        return {}

def _fetch_nhl_ratings(year, headers):
    """Fetch NHL Ratings from API-Sports."""
    ratings = {}
    try:
        nhl_headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
        nhl_id = 57 # Standard ID
        nhl_season = int(year) 
        
        url = f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season={nhl_season}"
        res = requests.get(url, headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) == 0:
            # Fallback
            res = requests.get(f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season={nhl_season-1}", headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) > 0:
            flattened = [item for sublist in res['response'] for item in sublist]
            
            total_goals = 0
            total_games = 0
            for row in flattened:
                gp = row['games']['played']
                gf = row['goals']['for']
                if gp > 0:
                    total_goals += _num(gf, 0)
                    total_games += _num(gp, 0)

            avg_goals = (total_goals / total_games) if total_games > 0 else 3.0

            for row in flattened:
                name = row['team']['name']
                gp = row['games']['played']
                if _num(gp, 0) < 5: continue

                gf_avg = _num(row['goals']['for'], 0) / _num(gp, 1)
                ga_avg = _num(row['goals']['against'], 0) / _num(gp, 1)

                ratings[name] = {
                    'attack': gf_avg / avg_goals,
                    'defense': ga_avg / avg_goals,
                    'league_avg_goals': avg_goals,
                    'sport': 'NHL'
                }
        return ratings
    except Exception as e:
        log("ERROR", f"NHL Ratings failed: {e}")
        return {}

def _fetch_ncaab_ratings(year, headers):
    """Fetch NCAAB Ratings from KenPom."""
    ratings = {}
    try:
        kp_headers = {'Authorization': f'Bearer {Config.KENPOM_API_KEY}'}
        url = f"https://kenpom.com/api.php?endpoint=ratings&y={year}"
        
        res = requests.get(url, headers=kp_headers, timeout=10)
        if res.status_code == 200:
            raw_ratings = res.json()
            for t in raw_ratings:
                ratings[t['TeamName']] = {
                    'offensive_eff': float(t['AdjOE']),
                    'defensive_eff': float(t['AdjDE']),
                    'tempo': float(t['AdjTempo']),
                    'sport': 'NCAAB'
                }
        return ratings
    except Exception as e:
        log("ERROR", f"NCAAB Ratings failed: {e}")
        return {}

def _fetch_nba_ratings(year, headers):
    """Fetch NBA Ratings from TeamRankings."""
    ratings = {}
    try:
        def fetch_nba_stat(metric, key_name):
            try:
                r_nba = requests.get(f"https://www.teamrankings.com/nba/stat/{metric}", headers=headers, timeout=10)
                df_nba = pd.read_html(StringIO(r_nba.text))[0]
                # Try finding current year or next year (season logic varies)
                col_nba = next((c for c in df_nba.columns if year in str(c) or str(int(year)+1) in str(c)), 'Last 3')
                
                for _, row_n in df_nba.iterrows():
                    tm = str(row_n['Team'])
                    val_n = str(row_n[col_nba]).replace('%', '')
                    try:
                        f_val = float(val_n)
                        # Normalize EFG% or standard metrics? 
                        # Logic from original: if < 20.0 assume it needs *100? 
                        # Original: if f_val < 20.0: f_val *= 100
                        if f_val < 20.0: f_val *= 100
                        
                        if tm not in ratings: ratings[tm] = {'sport': 'NBA'}
                        ratings[tm][key_name] = f_val
                    except:
                        continue
            except Exception as ex:
                log("ERROR", f"NBA {key_name} fetch failed: {ex}")

        fetch_nba_stat('offensive-efficiency', 'offensive_eff')
        fetch_nba_stat('defensive-efficiency', 'defensive_eff')
        fetch_nba_stat('possessions-per-game', 'tempo')
        
        return ratings
    except Exception as e:
        log("ERROR", f"NBA Ratings failed: {e}")
        return {}


from data.cache import cache_get, cache_set

def get_team_ratings():
    """
    Fetch team ratings from multiple sources in parallel.
    RETURNS:
        dict: Merged dictionary of all ratings.
    """
    # Cache Check (1 Hour TTL)
    cached = cache_get('team_ratings', ttl_seconds=3600)
    if cached:
        log("RATINGS", "✅ Using Cached Ratings")
        return cached

    log("RATINGS", "Fetching KenPom, NBA, NHL, and NFL data (Parallel)...")
    
    nfl_year, kenpom_year = get_current_seasons()
    # Headers for TeamRankings/general use
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    combined_ratings = {}
    
    expected_sports = {'NFL', 'NHL', 'NCAAB', 'NBA'} # ideally dynamic from Config
    failed_sports = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit tasks
        futures = {
            executor.submit(_fetch_nfl_ratings, nfl_year, headers): "NFL",
            executor.submit(_fetch_nhl_ratings, nfl_year, headers): "NHL", # Uses same base year logic usually
            executor.submit(_fetch_ncaab_ratings, kenpom_year, headers): "NCAAB",
            executor.submit(_fetch_nba_ratings, nfl_year, headers): "NBA"
        }
        
        for future in as_completed(futures):
            sport = futures[future]
            try:
                data = future.result()
                if data:
                    combined_ratings.update(data)
                    log("RATINGS", f"✅ Loaded {len(data)} {sport} ratings")
                else:
                    log("ERROR", f"{sport} ratings returned empty data")
                    failed_sports.append(sport)
            except Exception as e:
                log("ERROR", f"{sport} fetch crashed: {e}")
                failed_sports.append(sport)
                
    # Cache Set ONLY if No Failures
    if not failed_sports and combined_ratings:
        cache_set('team_ratings', combined_ratings)
    elif failed_sports:
        log("WARN", f"Skipping Cache Update due to failures in: {failed_sports}")
        
    return combined_ratings
