
import sys
import os
# Add root to path for imports
sys.path.append(os.getcwd())

import psycopg2
from db.connection import get_db

def backfill_pushes():
    print("♻️ Starting Totals Push Backfill...")
    conn = get_db()
    if not conn:
        print("❌ DB Connection failed")
        return

    try:
        cur = conn.cursor()
        
        # Select PENDING Over/Under bets where game is finished
        # Note: We need the score to check (not just pending)
        # Assuming we can re-grade from processing.grading if we had scores.
        # But for backfill, we might need to fetch scores again or rely on what's in intelligence_log if we stored scores?
        # intelligence_log doesn't store scores.
        
        # Strategy:
        # 1. Re-run `settle_pending_bets()` from grading.py
        #    Now that the code is fixed, it should catch the Pushes IF it fetches the games.
        #    But `settle_pending_bets` fetches "Today + 4 Days back". 
        #    If the PUSH is older than 4 days, settle_pending won't see it.
        
        # ALTERNATIVE:
        # We need to target specific PENDING bets in db and check them.
        # Let's import the grading logic.
        
        from processing.grading import settle_pending_bets
        
        # We can temporarily Monkey-Patch the date range in settle_pending_bets?
        # Or just manually force a deep check.
        
        print("   Triggering standard settlement to catch recent Pushes...")
        settle_pending_bets()
        
        # For OLDER bets (Deep Clean):
        # We need to query intelligence_log for PENDING O/U bets older than 5 days.
        cur.execute("""
            SELECT event_id, selection, teams, kickoff 
            FROM intelligence_log 
            WHERE outcome = 'PENDING' 
              AND (selection LIKE '%Over%' OR selection LIKE '%Under%')
              AND kickoff < NOW() - INTERVAL '5 DAYS'
        """)
        old_pendings = cur.fetchall()
        
        if not old_pendings:
            print("   No old pending O/U bets (>5 days) found.")
        else:
            print(f"   Found {len(old_pendings)} old pending O/U bets. Manual review needed or score fetch required.")
            for row in old_pendings:
                print(f"   - {row[1]} ({row[2]}) Date: {row[3]}")
                
            # If there were any, we'd need to fetch historical scores from ESPN for those dates.
            # For now, let's assume the user cares about recent/active portfolio.
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()
        print("✅ Backfill Run Complete.")

if __name__ == "__main__":
    backfill_pushes()
