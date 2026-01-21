import requests
from config import Config
from database import get_db, safe_execute
from utils import log

# ---------------------------
# Helper: Name Normalization
# ---------------------------
def normalize_name(name):
    """Normalize team names for fuzzy matching."""
    if not name: return ""
    n = name.lower()
    # Common NCAA/Sport abbreviations
    replacements = {
        "st.": "state",
        "state": "st",  # Normalized checks will compare both ways ideally, but simple replace helps
        "uconn": "connecticut",
        "ole miss": "mississippi",
        "penn state": "penn st",
        "nc state": "nc st",
        "n.c. state": "nc st",
        "miami (fl)": "miami",
        "miami (oh)": "miami",
        "massachusetts": "umass",
        "central michigan": "c michigan", # ESPN sometimes does this
        "western michigan": "w michigan",
        "eastern michigan": "e michigan"
    }
    for k, v in replacements.items():
        if k in n:
            n = n.replace(k, v)
    
    # Remove rank numbers (e.g. "(12) Name")
    # Simple check: remove parenthesis
    n = n.replace("(", "").replace(")", "")
    return n.strip()

def fuzzy_match(team1, team2):
    """Check if two team names likely refer to the same entity."""
    n1 = normalize_name(team1)
    n2 = normalize_name(team2)
    
    # Direct match
    if n1 in n2 or n2 in n1:
        return True
        
    # Token set match
    t1 = set(n1.split())
    t2 = set(n2.split())
    
    # If one is a subset of the other (with at least 50% overlap of shorter)
    intersection = t1.intersection(t2)
    if len(intersection) >= min(len(t1), len(t2)) * 0.6:
        return True
        
    return False

# ---------------------------
# Grading Logic
# ---------------------------
def grade_bet(selection, home_team, away_team, home_score, away_score):
    """Grades a single leg wager."""
    
    margin = home_score - away_score
    
    # Normalize for safety
    h_norm = normalize_name(home_team)
    a_norm = normalize_name(away_team)
    
    # 1. Moneyline
    if " ML" in selection and "Draw" not in selection:
        pick = selection.replace(" ML", "").replace("1H", "").replace("1st Half", "").strip()
        pick_norm = normalize_name(pick)
        
        pick_is_home = fuzzy_match(pick, home_team)
        pick_is_away = fuzzy_match(pick, away_team)

        if margin > 0 and pick_is_home: return 'WON'
        if margin < 0 and pick_is_away: return 'WON'
        if margin == 0: return 'PUSH'
        return 'LOST'

    # 2. Soccer Draws
    if selection == "Draw ML":
        return 'WON' if margin == 0 else 'LOST'

    # 3. Spreads
    # Allow '(' for team names like 'Loyola (Chi)', but ensure it's not a Parlay wrapper if strictly checking
    # But grade_bet is called for specific legs too.
    if ('+' in selection or '-' in selection) and "Parlay" not in selection:
        try:
            # Parse "Team +X.5"
            # Handle potential suffix like " (-110)" if present, though usually sanitized before
            parts = selection.rsplit(' ', 1)
            raw_team, spread_str = parts[0].strip(), parts[1]
            try:
                spread = float(spread_str)
            except ValueError:
                # Retry if spread is inside parens or something weird?
                # Assume standard format for now
                return 'PENDING'

            pick_is_home = fuzzy_match(raw_team, home_team)
            pick_is_away = fuzzy_match(raw_team, away_team)
            
            cov = 0
            if pick_is_home:
                cov = margin + spread
            elif pick_is_away:
                cov = -margin + spread
            else:
                return 'PENDING' # Name mismatch
            
            if cov > 0: return 'WON'
            if cov < 0: return 'LOST'
            return 'PUSH'
        except:
            pass

    # 4. Over/Under
    if "Over" in selection or "Under" in selection:
        try:
            # Clean selection: remove "Goals", "Points", "Runs"
            clean_sel = selection.lower().replace(" goals", "").replace(" points", "").replace(" runs", "")
            val = float(clean_sel.split()[-1])
            total = home_score + away_score
            if "Over" in selection: return 'WON' if total > val else 'LOST'
            if "Under" in selection: return 'WON' if total < val else 'LOST'
        except:
            pass

    return 'PENDING'

def grade_parlay(selection, all_games):
    """
    Grades a parlay by checking ALL legs against the fetched games.
    Args:
        selection: "Parlay (3 Legs): Leg 1 + Leg 2 + Leg 3"
        all_games: List of game dicts from ESPN
    """
    if "Parlay" not in selection and "Legs" not in selection:
        return 'PENDING'
        
    # Extract legs
    # Format: "Parlay (X Legs): Leg 1 + Leg 2"
    try:
        content = selection.split("):")[1].strip()
        legs = [l.strip() for l in content.split(" + ")]
    except:
        return 'PENDING'
        
    results = []
    
    for leg in legs:
        # Find the game for this leg
        # Heuristic: The leg usually contains one of the team names
        # We need to scan ALL games to find a match
        leg_outcome = 'PENDING'
        
        # Extract team name from leg (simplified)
        # Leg format: "Team ML" or "Team +X" or "Over X"
        # Over/Under is hard to match without team context in string. 
        # But Sniper Triple usually has "Team ML" or "Team Spread".
        
        target_team = None
        if " ML" in leg:
            target_team = leg.replace(" ML", "").strip()
        elif "Over" in leg or "Under" in leg:
             # O/U in parlay is hard unless we map it to the game. 
             # Assuming we skip O/U parlay legs for now or fuzzy match row content?
             # Actually, for this specific user's parlay, it's mixed.
             pass
        else:
            # Spread likely: "Team +X"
            target_team = leg.rsplit(' ', 1)[0].strip()
            
        found_game = None
        if target_team:
            for g in all_games:
                if fuzzy_match(target_team, g['home']) or fuzzy_match(target_team, g['away']):
                    found_game = g
                    break
        
        if found_game:
            # Check if game is complete
            if found_game.get('is_complete') or "Final" in found_game['status']:
                # Grade this leg
                leg_outcome = grade_bet(leg, found_game['home'], found_game['away'], 
                                        found_game['home_score'], found_game['away_score'])
            else:
                leg_outcome = 'PENDING'
        else:
            leg_outcome = 'PENDING' # Game not found in fetch (maybe different day)
            
        results.append(leg_outcome)

    if 'LOST' in results:
        return 'LOST'
    if all(r == 'WON' for r in results):
        return 'WON'
        
    return 'PENDING'


def settle_pending_bets():
    """Check for pending bets that can be graded and update their outcomes."""
    log("GRADING", "Checking for pending bets to settle...")
    conn = get_db()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        # 1. Fetch live/recent scores from ESPN (Today + Yesterday)
        keys = ['NBA', 'NCAAB', 'NHL', 'NFL', 'SOCCER'] 
        live_games = []
        
        try:
            from api_clients import fetch_espn_scores
            from datetime import datetime, timedelta
            import pytz
            
            tz = pytz.timezone('US/Eastern')
            now_et = datetime.now(tz)
            
            # Fetch Today and Yesterday to ensure we catch late finishes
            dates_to_fetch = [
                now_et.strftime('%Y%m%d'), 
                (now_et - timedelta(days=1)).strftime('%Y%m%d')
            ]
            
            for d in dates_to_fetch:
                log("GRADING", f"Fetching scores for date: {d}")
                g_day = fetch_espn_scores(keys, specific_date=d)
                live_games.extend(g_day)
                
            log("GRADING", f"Fetched {len(live_games)} games total.")
                
        except Exception as e:
            log("ERROR", f"Failed to fetch scores: {e}")
            return

        if not live_games:
            log("GRADING", "No live/recent games found.")
            return

        graded_count = 0
        
        # Re-query all pending bets
        cur.execute("SELECT event_id, sport, selection, teams FROM intelligence_log WHERE outcome = 'PENDING' AND kickoff < NOW()")
        pending_detailed = cur.fetchall()
        
        log("GRADING", f"Checking {len(pending_detailed)} pending bets against {len(live_games)} games.")

        for event_id, sport, selection, teams_str in pending_detailed:
             
             outcome = 'PENDING'
             
             # --- PARLAY LOGIC ---
             if sport == 'PARLAY' or 'Parlay' in selection:
                 outcome = grade_parlay(selection, live_games)
                 if outcome == 'PENDING':
                     pass # log("DEBUG", f"Parlay {event_id} still pending.")
                 
             # --- STANDARD LOGIC ---
             else:
                 # Find the specific game for this bet
                 matched_game = None
                 for g in live_games:
                     # Check direct team match
                     if fuzzy_match(g['home'], teams_str) and fuzzy_match(g['away'], teams_str):
                         matched_game = g
                         break
                     # Reverse
                     if fuzzy_match(g['away'], teams_str) and fuzzy_match(g['home'], teams_str):
                         matched_game = g
                         break
                         
                 if matched_game:
                     # Check if complete
                     if matched_game.get('is_complete') or "Final" in matched_game['status']:
                         try:
                             outcome = grade_bet(selection, matched_game['home'], matched_game['away'], 
                                                 matched_game['home_score'], matched_game['away_score'])
                             if outcome == 'PENDING':
                                 log("DEBUG", f"Bet {event_id} ({selection}) Matched but Graded PENDING. (Game: {matched_game['shortName']}, Score: {matched_game['home_score']}-{matched_game['away_score']})")
                         except Exception as e:
                             log("ERROR", f"Grading calc error {event_id}: {e}")
                     else:
                        pass # Game found but not final

             # UPDATE DB if Graded
             if outcome in ['WON', 'LOST', 'PUSH']:
                 safe_execute(cur, "UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, event_id))
                 graded_count += 1
                 log("GRADING", f"✅ Graded {event_id} ({sport}): {outcome}")

        conn.commit()

        if graded_count > 0:
            log("GRADING", f"✨ Successfully graded {graded_count} bets.")
        else:
            log("GRADING", "No new bets graded (waiting for games to finish or fuzzy match).")

    except Exception as e:
        log("ERROR", f"Grading run failed: {e}")
    finally:
        cur.close()
        conn.close()
