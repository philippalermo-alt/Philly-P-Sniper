import os
import psycopg2
import pandas as pd

def backfill():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='require')
        cur = conn.cursor()
        
        # Pull games that have market data
        cur.execute("SELECT event_id, money_pct, ticket_pct FROM intelligence_log WHERE money_pct IS NOT NULL")
        rows = cur.fetchall()
        
        if not rows:
            print("✅ No games with market data found.")
            return

        print(f"🔄 Recalculating {len(rows)} games with Gap-First logic...")
        for r in rows:
            eid, m_val, t_val = r[0], float(r[1]), float(r[2])
            
            # --- 📐 The 55/25/20 Sharp Score Math ---
            gap = m_val - t_val
            gap_score = max(0, min(1, (gap - 5) / 25))
            minority_score = max(0, min(1, (55 - t_val) / 25))
            money_majority_score = max(0, min(1, (m_val - 50) / 20))
            
            # This remains the raw intensity score
            sharp_val = round(100 * (0.55 * gap_score + 0.25 * minority_score + 0.20 * money_majority_score))
            
            # Update the database
            cur.execute("UPDATE intelligence_log SET sharp_score = %s WHERE event_id = %s", (sharp_val, eid))
        
        conn.commit()
        print(f"✅ Successfully updated {len(rows)} sharp scores.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Backfill Error: {e}")

if __name__ == "__main__":
    backfill()
