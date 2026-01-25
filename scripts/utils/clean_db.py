
import os
from database import get_db

def clean_db():
    print("🧹 Starting Database Cleanup...")
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return
        
    try:
        cur = conn.cursor()
        
        # 1. Delete "oNone" selections
        # Search for string literal "oNone" in selection or market
        # Also clean up any "Goalscorer oNone"
        
        print("🔍 Searching for corrupted records...")
        cur.execute("""
            SELECT count(*) FROM intelligence_log 
            WHERE selection LIKE '%oNone%' 
            OR market LIKE '%oNone%'
            OR event_id LIKE '%oNone%'
        """)
        count = cur.fetchone()[0]
        
        if count > 0:
            print(f"⚠️ Found {count} corrupted records. Deleting...")
            cur.execute("""
                DELETE FROM intelligence_log 
                WHERE selection LIKE '%oNone%' 
                OR market LIKE '%oNone%'
                OR event_id LIKE '%oNone%'
            """)
            conn.commit()
            print("✅ Records deleted.")
        else:
            print("✅ No corrupted 'oNone' records found.")
            
        # 2. Delete rows with invalid team_id in player_stats?
        # NO - Too risky to do blindly. Code patch handles the read side.
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    clean_db()
