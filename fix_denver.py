from database import get_db
import datetime

def fix_denver():
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # 1. Update Timestamp for NE@DEN to appearing 'Fresh'
        print("Updating Timestamp for NE@DEN...")
        cur.execute("""
            UPDATE intelligence_log 
            SET timestamp = NOW() 
            WHERE teams ILIKE '%New England%' AND selection='Under 43.5'
        """)
        
        # 2. Check splits and Update Score
        cur.execute("""
            SELECT money_pct, ticket_pct, sharp_score 
            FROM intelligence_log 
            WHERE teams ILIKE '%New England%' AND selection='Under 43.5'
        """)
        row = cur.fetchone()
        
        m_val, t_val = row[0], row[1]
        
        if m_val is None: m_val = 0
        if t_val is None: t_val = 0
        
        # New Formula Calculation
        gap = m_val - t_val
        gap_score = max(0, min(1, (gap - 0) / 15)) 
        minority_score = max(0, min(1, (55 - t_val) / 25))
        money_majority_score = max(0, min(1, (m_val - 50) / 20))
        
        new_score = int(round(100 * (0.60 * gap_score + 0.30 * minority_score + 0.10 * money_majority_score)))
        
        print(f"Stats: Money={m_val}%, Tickets={t_val}% -> Gap={gap}%")
        print(f"Old Score={row[2]} -> New Score={new_score}")
        
        cur.execute("""
            UPDATE intelligence_log 
            SET timestamp = NOW(), sharp_score = %s
            WHERE teams ILIKE '%%New England%%' AND selection='Under 43.5'
        """, (new_score,))
        
        conn.commit()
        print("✅ Denver Fixed (Timestamp + Score).")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    fix_denver()
