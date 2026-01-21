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

        # Map Sport Column to Internal Keys (for api_clients.py)
        sport_map = {
            'NBA': 'NBA',
            'NCAAB': 'NCAAB',
            'NFL': 'NFL',
            'NHL': 'NHL',
            'EPL': 'SOCCER',
            'LALIGA': 'LALIGA',
            'CHAMP': 'SOCCER', # Fallback for Championship to generic English soccer if mapped
            'MLB': 'MLB',
            'SOCCER': 'SOCCER',
            'BUNDESLIGA': 'BUNDESLIGA',
            'SERIEA': 'SERIEA',
            'LIGUE1': 'LIGUE1',
            'CHAMPIONS': 'CHAMPIONS'
        }

        # Gather relevant sport keys
        active_sports = set()
        for p in pending:
            s_key = p[1]
            mapped = sport_map.get(s_key, s_key) # Default to self if not in map
            active_sports.add(mapped)

        log("GRADING", f"Fetching LIVE scores for: {list(active_sports)} (Source: ESPN)")
        
        from api_clients import fetch_espn_scores
        live_games = fetch_espn_scores(list(active_sports))
        
        if not live_games:
            log("GRADING", "No live/recent games found.")
            return

        graded = 0
        
        # Re-query with teams column included before looping live games
        cur.execute("SELECT event_id, sport, selection, teams FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")
        pending_detailed = cur.fetchall()

        # Grading Logic
        for game in live_games:
            # We only grade if game is "Completed" (Final)
            if not game.get('is_complete') and "Final" not in game['status']:
                continue

            home = game['home']
            away = game['away']
            h_score = game['home_score']
            a_score = game['away_score']
            
            # Use 'sport' from game dict; fallback to None if not present
            g_sport = game.get('sport')

            # Check ALL pending bets against THIS game
            for event_id, ps_sport, selection, teams_str in pending_detailed:
                 
                 # Optimization: specific sport check if reliable
                 # if g_sport and ps_sport not in g_sport: continue
                 
                 # Match logic: Checks if ESPN names are loosely in DB names
                 # DB: "Philadelphia 76ers vs Boston Celtics"
                 # ESPN: "76ers" vs "Celtics" (often shorter)
                 
                 # Clean match check
                 match_found = False
                 
                 # Case 1: Loose containment
                 if home in teams_str and away in teams_str:
                     match_found = True
                 # Case 2: Reverse
                 elif away in teams_str and home in teams_str:
                     match_found = True
                     
                 if match_found:
                     # Grade it
                     try:
                         outcome = grade_bet(selection, home, away, h_score, a_score, period_scores=None)
                         if outcome and outcome != 'PENDING':
                             safe_execute(cur, "UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, event_id))
                             graded += 1
                             log("GRADING", f"✅ Graded {event_id}: {selection} -> {outcome}")
                     except Exception as e:
                         log("ERROR", f"Grading error {event_id}: {e}")

        conn.commit()

        if graded > 0:
            log("GRADING", f"✨ Successfully graded {graded} bets via ESPN (Free).")

    except Exception as e:
        log("ERROR", f"Grading run failed: {e}")
    finally:
        cur.close()
        conn.close()
