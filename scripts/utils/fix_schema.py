
import psycopg2
from config import Config

def fix_schema():
    print("🔧 Applying Schema Patch for KenPom Stats...")
    try:
        conn = psycopg2.connect(Config.DATABASE_URL)
        cur = conn.cursor()
        
        cols = [
            "home_adj_em REAL", "away_adj_em REAL",
            "home_adj_o REAL", "away_adj_o REAL",
            "home_adj_d REAL", "away_adj_d REAL",
            "home_tempo REAL", "away_tempo REAL"
        ]
        
        for col in cols:
            print(f"   -> Adding {col}...")
            try:
                cur.execute(f"ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS {col}")
            except Exception as e:
                print(f"      (Info: {e})")
                conn.rollback()
            else:
                conn.commit()
                
        print("✅ Schema Patch Complete.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to connect or patch: {e}")

if __name__ == "__main__":
    fix_schema()
