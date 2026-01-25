
import psycopg2
from config import Config
import pandas as pd

def inspect():
    print("🔍 Inspecting Database Intelligence Log...")
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
        cur = conn.cursor()
        
        # 1. Check Max Timestamp
        cur.execute("SELECT MAX(timestamp), MIN(timestamp), COUNT(*) FROM intelligence_log")
        row = cur.fetchone()
        print(f"\n📊 Stats:")
        print(f"   Total Rows: {row[2]}")
        print(f"   Min Time: {row[1]}")
        print(f"   Max Time: {row[0]}")
        
        # 2. Check for PRO Triggers
        print("\n🦅 Latest 5 'Pro System' or 'Sharp Signal' Bets:")
        cur.execute("""
            SELECT timestamp, sport, selection, trigger_type, sharp_score 
            FROM intelligence_log 
            WHERE trigger_type LIKE '%PRO:%' OR sharp_score >= 25 
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        rows = cur.fetchall()
        if not rows:
            print("   (No Pro System or High Sharp Score bets found recently)")
        else:
            for r in rows:
                print(f"   [{r[0]}] {r[1]} - {r[2]} (Trigger: {r[3]}) [Score: {r[4]}]")

        # 3. Check most recent raw entries
        print("\nRecent 5 Entries (Any Type):")
        cur.execute("SELECT timestamp, selection, trigger_type FROM intelligence_log ORDER BY timestamp DESC LIMIT 5")
        for r in cur.fetchall():
            print(f"   [{r[0]}] {r[1]} ({r[2]})")

        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ DB Read Failed: {e}")

if __name__ == "__main__":
    inspect()
