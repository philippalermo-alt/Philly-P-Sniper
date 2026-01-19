import os
import psycopg2

def reset_bets():
    # Connect to your Heroku Postgres database
    url = os.environ.get('DATABASE_URL')
    if not url:
        print("❌ ERROR: DATABASE_URL not found.")
        return

    try:
        conn = psycopg2.connect(url, sslmode='require')
        cur = conn.cursor()

        # This SQL statement flips 'WON' or 'LOST' back to 'PENDING'
        # only for games that kicked off in the last 6 hours.
        query = """
            UPDATE intelligence_log 
            SET outcome = 'PENDING' 
            WHERE outcome IN ('WON', 'LOST') 
            AND kickoff > (NOW() AT TIME ZONE 'UTC' - INTERVAL '6 hours');
        """
        
        cur.execute(query)
        count = cur.rowcount
        conn.commit()
        
        print(f"✅ SUCCESS: Reset {count} bets to PENDING.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ DATABASE ERROR: {e}")

if __name__ == "__main__":
    reset_bets()