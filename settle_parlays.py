import re
from database import get_db

def settle_parlays():
    print("🧩 Starting Parlay Settlement...")
    conn = get_db()
    if not conn: return
    
    cur = conn.cursor()
    
    # 1. Fetch Pending Parlays
    cur.execute("SELECT event_id, selection FROM intelligence_log WHERE sport='PARLAY' AND outcome='PENDING'")
    parlays = cur.fetchall()
    
    if not parlays:
        print("✅ No pending parlays.")
        return
        
    for pid, text in parlays:
        print(f"\nProcessing {pid}...")
        # Extract Legs: "Parlay (3 Legs): Leg 1 (Odds) + Leg 2 (Odds) + ..."
        # Regex to find parts between ": " and the end, split by " + "
        try:
            content = text.split(': ')[1]
            legs_raw = content.split(' + ')
            
            leg_statuses = []
            
            for leg in legs_raw:
                # leg format: "Team Name Market (Odds)" -> "UTEP Miners +1.5 (1.87)"
                # We need to match this to the 'selection' column in DB
                # Remove the odds part "(1.87)"
                leg_clean = re.sub(r'\s*\(\d+\.\d+\)$', '', leg).strip()
                
                # Search DB for this selection (most recent, non-parlay)
                print(f"  Checking Leg: '{leg_clean}'")
                
                # Careful: The single bet might be slightly different string or verified via teams
                # Let's try partial match on selection
                cur.execute("""
                    SELECT outcome FROM intelligence_log 
                    WHERE selection = %s 
                    AND sport != 'PARLAY'
                    ORDER BY timestamp DESC LIMIT 1
                """, (leg_clean,))
                
                row = cur.fetchone()
                if row:
                    status = row[0]
                    print(f"    -> Found Status: {status}")
                    leg_statuses.append(status)
                else:
                    print(f"    -> ⚠️ Single bet not found in DB!")
                    leg_statuses.append("UNKNOWN")

            # Grade Parlay
            if "LOST" in leg_statuses:
                final = "LOST"
            elif "UNKNOWN" in leg_statuses or "PENDING" in leg_statuses:
                final = "PENDING"
            elif all(s == "WON" for s in leg_statuses):
                final = "WON"
            else:
                final = "PENDING" # Fallback
            
            print(f"  📝 Final Decision: {final}")
            
            if final != "PENDING":
                cur.execute("UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (final, pid))
                conn.commit()
                print("  ✅ Updated DB")
                
        except Exception as e:
            print(f"  ❌ Error parsing parlay: {e}")

    conn.close()

if __name__ == "__main__":
    settle_parlays()
