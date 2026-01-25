from database import get_db

def audit():
    conn = get_db()
    if not conn:
        print("❌ Could not connect to DB (Tunnel down?)")
        return

    try:
        cur = conn.cursor()
        print("\n📊 Current Database Counts:")
        print("-" * 40)
        cur.execute("""
            SELECT league, season, count(*) 
            FROM matches 
            GROUP BY league, season 
            ORDER BY league, season
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"{r[0]:<15} {r[1]:<10} : {r[2]} matches")
            
        print("-" * 40)
        
        # Total
        cur.execute("SELECT count(*) FROM matches")
        total = cur.fetchone()[0]
        print(f"TOTAL MATCHES: {total}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    audit()
