from db.connection import get_db

def verify_deleted():
    conn = get_db()
    cur = conn.cursor()
    
    print("VERIFYING DELETION: Colorado St (Over/Under 139.5 @ 1.87)")
    
    cur.execute("""
        SELECT ctid, event_id, selection, odds, timestamp 
        FROM intelligence_log 
        WHERE teams ILIKE '%Colorado St%' 
        AND (selection ILIKE '%Over%' OR selection ILIKE '%Under%')
        ORDER BY timestamp DESC
    """)
    
    rows = cur.fetchall()
    found_target = False
    
    for r in rows:
        print(f"Row: {r}")
        if abs(float(r[3] or 0) - 1.87) < 0.01:
            print("❌ BAD: The duplicate (1.87) IS STILL HERE.")
            found_target = True
            
    if not found_target:
        print("✅ GOOD: No record with odds 1.87 found.")

if __name__ == "__main__":
    verify_deleted()
