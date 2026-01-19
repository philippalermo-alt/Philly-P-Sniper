import os
import psycopg2

def migrate():
    try:
        # Connect using your Heroku Environment Variable
        conn = psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='require')
        cur = conn.cursor()
        
        # Add the column only if it doesn't exist
        print("🔄 Checking database for sharp_score column...")
        cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS sharp_score INTEGER;")
        
        conn.commit()
        print("✅ Success! The 'sharp_score' column is now ready.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error during migration: {e}")

if __name__ == "__main__":
    migrate()
