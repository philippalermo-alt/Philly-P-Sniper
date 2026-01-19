import requests
from config import Config
from database import get_db, safe_execute
from utils import log

def grade_bet(selection, home_team, away_team, home_score, away_score, period_scores=None):
    """
    Grades wagers with specific support for 1st Half (1H) markets and team name cleaning.

    Args:
        selection: The bet selection string (e.g., "Team ML", "Team +5.0")
        home_team: Home team name
        away_team: Away team name
        home_score: Home team score
        away_score: Away team score
        period_scores: Optional list of period scores for 1H grading

    Returns:
        str: 'WON', 'LOST', 'PUSH', or 'PENDING'
    """
    # STEP 1: Identify if this is a 1H bet
    is_1h = any(term in selection for term in ["1H", "1st Half", "Halftime"])

    # STEP 2: Use period scores for 1H bets if they exist in the API response
    if is_1h and period_scores:
        try:
            h_1h = next((p['score'] for p in period_scores if p['name'] == home_team and '1' in p.get('description', '')), None)
            a_1h = next((p['score'] for p in period_scores if p['name'] == away_team and '1' in p.get('description', '')), None)

            if h_1h is not None and a_1h is not None:
                home_score, away_score = int(h_1h), int(a_1h)
        except:
            pass  # Fall back to provided scores if period extraction fails

    margin = home_score - away_score

    # 1. Moneyline
    if " ML" in selection:
        pick = selection.replace(" ML", "").replace("1H", "").replace("1st Half", "").strip().lower()

        pick_matches_home = pick in home_team.lower() or home_team.lower() in pick
        pick_matches_away = pick in away_team.lower() or away_team.lower() in pick

        if margin > 0 and pick_matches_home:
            return 'WON'
        if margin < 0 and pick_matches_away:
            return 'WON'
        if margin == 0:
            return 'PUSH'
        return 'LOST'

    # 2. Soccer Draws
    if selection == "Draw ML":
        return 'WON' if margin == 0 else 'LOST'

    # 3. Spreads
    if ('+' in selection or '-' in selection) and '(' not in selection:
        try:
            parts = selection.rsplit(' ', 1)
            raw_team, spread = parts[0].strip(), float(parts[1])

            clean_team = raw_team.replace("1H", "").replace("1st Half", "").strip().lower()

            matches_home = clean_team in home_team.lower() or home_team.lower() in clean_team
            matches_away = clean_team in away_team.lower() or away_team.lower() in clean_team

            if matches_home:
                cov = margin + spread
            elif matches_away:
                cov = -margin + spread
            else:
                return 'PENDING'  # Safety: Name still doesn't match

            if cov > 0:
                return 'WON'
            if cov < 0:
                return 'LOST'
            return 'PUSH'
        except:
            pass

    # 4. Over/Under
    if "Over" in selection or "Under" in selection:
        try:
            line = float(selection.split()[-1])
            total = home_score + away_score
            if "Over" in selection:
                return 'WON' if total > line else 'LOST'
            if "Under" in selection:
                return 'WON' if total < line else 'LOST'
        except:
            pass

    return 'PENDING'

def settle_pending_bets():
    """Check for pending bets that can be graded and update their outcomes."""
    log("GRADING", "Checking for pending bets to settle...")
    conn = get_db()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")
    pending_count = cur.fetchone()[0]
    log("GRADING", f"Found {pending_count} past-due bets waiting for scores.")

    conn = get_db()
    if not conn:
        return

    cur = conn.cursor()

    try:
        cur.execute("SELECT event_id, sport, selection FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")
        pending = cur.fetchall()

        if not pending:
            return

        sport_map = {
            'NBA': 'basketball_nba',
            'NCAAB': 'basketball_ncaab',
            'NFL': 'americanfootball_nfl',
            'NHL': 'icehockey_nhl',
            'EPL': 'soccer_epl',
            'LALIGA': 'soccer_spain_la_liga',
            'CHAMP': 'soccer_efl_champ',
            'MLB': 'baseball_mlb',
            'SOCCER': 'soccer_epl'  # Default fallback
        }

        graded = 0

        for sport in set([p[1] for p in pending]):
            league = sport_map.get(sport)
            if not league:
                continue

            try:
                url = f"https://api.the-odds-api.com/v4/sports/{league}/scores/?apiKey={Config.ODDS_API_KEY}&daysFrom=3"
                res = requests.get(url, timeout=10).json()

                if not isinstance(res, list):
                    continue

                for game in res:
                    if not game.get('completed') or not game.get('scores'):
                        continue

                    scores = {s['name']: int(s['score']) for s in game['scores']}
                    home, away = game['home_team'], game['away_team']

                    if home not in scores or away not in scores:
                        continue

                    for event_id, _, selection in pending:
                        if event_id.startswith(game['id']):
                            outcome = grade_bet(selection, home, away, scores[home], scores[away], game['scores'])

                            if outcome:
                                safe_execute(cur, "UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, event_id))
                                graded += 1

            except:
                pass

        conn.commit()

        if graded > 0:
            log("GRADING", f"Graded {graded} bets")

    except:
        pass
    finally:
        cur.close()
        conn.close()
