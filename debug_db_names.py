from db.connection import get_db

def find_db_names():
    conn = get_db()
    try:
        cur = conn.cursor()
        queries = [
            "%Atalanta%", "%Bergamo%"
        ]
        print("🔎 Searching for canonical team names...")
        for q in queries:
            cur.execute("SELECT DISTINCT home_team FROM matches WHERE home_team ILIKE %s", (q,))
            rows = cur.fetchall()
            if rows:
                print(f"   Query '{q}': {[r[0] for r in rows]}")
            else:
                print(f"   Query '{q}': NO MATCH")
    finally:
        conn.close()

if __name__ == "__main__":
    find_db_names()
