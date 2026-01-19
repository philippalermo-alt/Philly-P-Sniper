import requests
import pandas as pd
from io import StringIO
from config import Config
from utils import log, _num

def get_team_ratings():
    """
    Fetch team ratings from multiple sources (KenPom, TeamRankings, Hockey API).

    Returns:
        dict: Team ratings keyed by team name with sport-specific metrics
    """
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
            team = str(row['Team'])
            ratings[team] = {'sport': 'NFL'}
            ratings[team]['off_ypp'] = float(row['2024'])

        for _, row in def_ypp.iterrows():
            if str(row['Team']) in ratings:
                ratings[str(row['Team'])]['def_ypp'] = float(row['2024'])

        for _, row in off_ppg.iterrows():
            if str(row['Team']) in ratings:
                ratings[str(row['Team'])]['off_ppg'] = float(row['2024'])

        for _, row in def_ppg.iterrows():
            if str(row['Team']) in ratings:
                ratings[str(row['Team'])]['def_ppg'] = float(row['2024'])

        log("RATINGS", f"Loaded NFL ratings for {len([k for k,v in ratings.items() if v.get('sport')=='NFL'])} teams")

    except:
        pass

    # --- NHL ---
    try:
        nhl_headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}
        leagues = requests.get("https://v1.hockey.api-sports.io/leagues?name=NHL", headers=nhl_headers, timeout=10).json()

        nhl_id = 57
        if leagues.get('results', 0) > 0:
            nhl_id = leagues['response'][0]['id']

        url = f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season=2025"
        res = requests.get(url, headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) == 0:
            url = f"https://v1.hockey.api-sports.io/standings?league={nhl_id}&season=2024"
            res = requests.get(url, headers=nhl_headers, timeout=10).json()

        if res.get('results', 0) > 0:
            flattened = [item for sublist in res['response'] for item in sublist]

            total_goals = 0
            total_games = 0

            for row in flattened:
                try:
                    gp = row['games']['played']
                    gf = row['goals']['for']
                    if gp > 0:
                        total_goals += _num(gf, 0)
                        total_games += _num(gp, 0)
                except:
                    pass

            avg_goals = (total_goals / total_games) if total_games > 0 else 3.0

            for row in flattened:
                try:
                    name = row['team']['name']
                    gp = row['games']['played']

                    if _num(gp, 0) < 5:
                        continue

                    gf_avg = _num(row['goals']['for'], 0) / _num(gp, 1)
                    ga_avg = _num(row['goals']['against'], 0) / _num(gp, 1)

                    ratings[name] = {
                        'attack': gf_avg / avg_goals,
                        'defense': ga_avg / avg_goals,
                        'league_avg_goals': avg_goals,
                        'sport': 'NHL'
                    }

                except:
                    pass

            log("RATINGS", f"Loaded {len([r for r in ratings.values() if r['sport']=='NHL'])} NHL ratings")

    except Exception as e:
        print(f"   ⚠️ NHL fetch failed: {e}")

    # --- NCAAB ---
    try:
        kp_headers = {'Authorization': f'Bearer {Config.KENPOM_API_KEY}'}
        raw_ratings = requests.get("https://kenpom.com/api.php?endpoint=ratings&y=2026", headers=kp_headers, timeout=10).json()

        for t in raw_ratings:
            ratings[t['TeamName']] = {
                'offensive_eff': float(t['AdjOE']),
                'defensive_eff': float(t['AdjDE']),
                'tempo': float(t['AdjTempo']),
                'sport': 'NCAAB'
            }

        log("RATINGS", f"Loaded {len(raw_ratings)} KenPom ratings")

    except Exception as e:
        print(f"   ⚠️ KenPom error: {e}")

    # --- NBA ---
    try:
        url = 'https://www.teamrankings.com/nba/stat/offensive-efficiency'
        nba_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        df = pd.read_html(StringIO(requests.get(url, headers=nba_headers, timeout=10).text))[0]

        col = next((c for c in df.columns if '2024' in str(c) or '2025' in str(c) or 'Last' in str(c)), None)

        if col:
            for _, row in df.iterrows():
                val = float(str(row[col]).replace('%', ''))

                if val < 20.0:
                    val = val * 100

                ratings[str(row['Team'])] = {
                    'offensive_eff': val,
                    'defensive_eff': 110.0,
                    'tempo': 100.0,
                    'sport': 'NBA'
                }

            log("RATINGS", "Loaded NBA ratings")

    except Exception as e:
        print(f"   ⚠️ NBA error: {e}")

    return ratings
