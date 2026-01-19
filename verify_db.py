import os
import psycopg2

def check():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='require')
        cur = conn.cursor()
        print("📊 --- Outcome Distribution ---")
        cur.execute("SELECT outcome, count(*) FROM intelligence_log GROUP BY outcome")
        for row in cur.fetchall():
            print(f"{row[0]}: {row[1]}")
        print("\n✅ --- Last 5 Graded Bets ---")
        cur.execute("SELECT kickoff, teams, selection, outcome FROM intelligence_log WHERE outcome IN ('WON', 'LOST') ORDER BY kickoff DESC LIMIT 5")
        for row in cur.fetchall():
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check()