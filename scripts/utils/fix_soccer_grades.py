from database import get_db

def fix_soccer_grades():
    conn = get_db()
    cur = conn.cursor()
    
    print("⚽️ Checking for incorrect Soccer PUSH grades...")
    
    # 1. Fix "Draw ML" that were PUSHed (Should be WON)
    # Why? Because they fell into generic ML logic which returned PUSH on ties.
    cur.execute("SELECT count(*) FROM intelligence_log WHERE selection = 'Draw ML' AND outcome = 'PUSH'")
    draw_pushes = cur.fetchone()[0]
    
    if draw_pushes > 0:
        print(f"   > Found {draw_pushes} 'Draw ML' bets marked as PUSH. corrected to WON.")
        cur.execute("UPDATE intelligence_log SET outcome = 'WON' WHERE selection = 'Draw ML' AND outcome = 'PUSH'")
    else:
        print("   > No 'Draw ML' PUSH errors found.")
        
    # 2. Fix "Team ML" in SOCCER that were PUSHed (Should be LOST)
    # Why? Regular ML in 3-way markets loses on a Draw.
    # We filter by sport='SOCCER' and selection containing 'ML' but NOT 'Draw'
    cur.execute("SELECT count(*) FROM intelligence_log WHERE sport='SOCCER' AND outcome = 'PUSH' AND selection LIKE '% ML%' AND selection NOT LIKE '%Draw%'")
    team_pushes = cur.fetchone()[0]
    
    if team_pushes > 0:
        print(f"   > Found {team_pushes} Soccer 'Team ML' bets marked as PUSH. corrected to LOST.")
        cur.execute("UPDATE intelligence_log SET outcome = 'LOST' WHERE sport='SOCCER' AND outcome = 'PUSH' AND selection LIKE '% ML%' AND selection NOT LIKE '%Draw%'")
    else:
        print("   > No Soccer 'Team ML' PUSH errors found.")
        
    conn.commit()
    print("✅ Correction complete.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    fix_soccer_grades()
