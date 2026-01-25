from database import get_db
from utils import log

def check_local():
    conn = get_db()
    if not conn:
        print("❌ Could not connect to local DB.")
        return
        
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*), league, season FROM player_stats GROUP BY league, season")
        rows = cur.fetchall()
        
        print(f"📊 LOCAL DATA VERIFICATION:")
        total = 0
        for count, league, season in rows:
            print(f"   - {league} {season}: {count} rows")
            total += count
            
        if total > 0:
            print(f"✅ Total Rows: {total}. Ready to migrate.")
        else:
            print("⚠️ Local table is empty. Cannot migrate.")
            
    except Exception as e:
        print(f"Error checking verification: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_local()
