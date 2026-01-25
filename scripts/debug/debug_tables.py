import sqlite3
import os

DB_NAME = "/Users/purdue2k5/Documents/Philly-P-Sniper/sports_betting.db"

def check_db():
    print(f"📂 Checking DB: {DB_NAME}")
    if not os.path.exists(DB_NAME):
        print("❌ File does not exist!")
        return
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    print("🔎 Tables found:")
    tables = c.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    found_matches = False
    for t in tables:
        print(f" - {t[0]}")
        if t[0] == 'matches':
            found_matches = True
            
    if found_matches:
        print("✅ 'matches' table EXISTS.")
    else:
        print("❌ 'matches' table NOT FOUND.")
        
    conn.close()

if __name__ == "__main__":
    check_db()
