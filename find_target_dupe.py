from db.connection import get_db

def locate_specific_dupe():
    conn = get_db()
    cur = conn.cursor()
    
    print("SEARCHING SPECIFIC: Colorado St @ San Diego St (Over)...")
    
    # Select CTID for deletion referencing
    cur.execute("""
        SELECT ctid, event_id, selection, odds, timestamp, teams
        FROM intelligence_log 
        WHERE teams ILIKE '%Colorado St%' AND teams ILIKE '%San Diego St%'
        AND selection ILIKE '%Over%'
        ORDER BY timestamp DESC
    """)
    
    rows = cur.fetchall()
    found_target = False
    
    if not rows:
        print("❌ No records found.")
    else:
        for r in rows:
            ctid, eid, sel, odds, ts, tms = r
            print(f"FOUND: {ts} | {sel} | Odds: {odds} | CTID: {ctid}")
            
            if abs(float(odds) - 1.87) < 0.01:
                print("   🎯 TARGET IDENTIFIED (Odds 1.87)")
                found_target = True

if __name__ == "__main__":
    locate_specific_dupe()
