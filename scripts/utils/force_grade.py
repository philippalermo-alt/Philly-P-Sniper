from bet_grading import settle_pending_bets
from api_clients import fetch_espn_scores
from database import get_db, safe_execute
from utils import log, normalize_team_name
from bet_grading import grade_bet, fuzzy_match
import datetime

def force_grade_wide_range():
    print("🚀 Force Grading Last 5 Days...")
    
    # Custom Grading Logic to replicate settle_pending_bets but with wider dates
    dates = ['20260120', '20260121', '20260122', '20260123']
    
    all_games = []
    for d in dates:
        print(f"  Fetching {d}...")
        all_games.extend(fetch_espn_scores(['NCAAB', 'NBA', 'NHL'], specific_date=d))
        
    print(f"  Loaded {len(all_games)} completed games.")
    
    conn = get_db()
    cur = conn.cursor()
    
    # Fetch PENDING
    cur.execute("SELECT event_id, sport, selection, teams, kickoff FROM intelligence_log WHERE outcome = 'PENDING'")
    pending = cur.fetchall()
    
    print(f"  Checking {len(pending)} pending bets...")
    
    graded = 0
    for pid, sport, sel, teams, kickoff in pending:
        # Standardize matching
        matched_game = None
        
        # Heuristic: Teams string usually "Away @ Home"
        try:
            db_away, db_home = teams.split(' @ ')
        except:
            db_away, db_home = teams, teams
            
        for g in all_games:
            # Check Home
            h_match = fuzzy_match(db_home, g['home'])
            a_match = fuzzy_match(db_away, g['away'])
            
            # Special Case: "Unknown Arena" or Weird names
            # IUPUI Check
            if "IUPUI" in db_away and ("IU" in g['away'] or "Indianapolis" in g['away']):
                 h_match = True
                 a_match = True
            
            if h_match and a_match:
                matched_game = g
                break
                
        if matched_game and (matched_game.get('is_complete') or "Final" in matched_game['status']):
            print(f"  MATCHED: {teams} -> {matched_game['away']} @ {matched_game['home']} ({matched_game['score_text']})")
            
            outcome = grade_bet(sel, matched_game['home'], matched_game['away'], 
                                matched_game['home_score'], matched_game['away_score'], sport=sport)
            
            if outcome in ['WON', 'LOST', 'PUSH']:
                print(f"    ✅ Grading {sel} -> {outcome}")
                safe_execute(cur, "UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, pid))
                graded += 1
            else:
                 print(f"    ⚠️ Could not grade outcome: {outcome}")

    conn.commit()
    conn.close()
    print(f"🏁 Force Grade Complete. Updated {graded} bets.")

if __name__ == "__main__":
    force_grade_wide_range()
