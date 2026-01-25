from database import get_db

def fix_draws():
    conn = get_db()
    cur = conn.cursor()
    
    # Check count before
    cur.execute("SELECT count(*) FROM intelligence_log WHERE selection = 'Draw ML' AND outcome = 'PUSH'")
    before = cur.fetchone()[0]
    print(f"Propagating fix for {before} Draw bets marked as PUSH...")
    
    # Fix
    cur.execute("UPDATE intelligence_log SET outcome = 'PENDING' WHERE selection = 'Draw ML' AND outcome = 'PUSH'")
    conn.commit()
    
    # Check count after
    cur.execute("SELECT count(*) FROM intelligence_log WHERE selection = 'Draw ML' AND outcome = 'PENDING'")
    after = cur.fetchone()[0]
    print(f"Updated. Now {after} Draw bets are PENDING.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_draws()
