from db.connection import get_db

def run_migration():
    """
    One-time cleanup for Duplicate Bets (Jan 28, 2026).
    Deletes the specific duplicate 'Under 139.5 @ 1.87' for Colorado/SDSU.
    """
    conn = get_db()
    if not conn:
        print("❌ [MIGRATION] DB Connection Failed.")
        return

    try:
        cur = conn.cursor()
        print("🧹 [MIGRATION] Running duplicate cleanup...")
        
        # 1. Delete the specific duplicate (Odds 1.87 Under for Colo/SDSU)
        # Using specific criteria rather than CTID (CTID varies by DB)
        cur.execute("""
            DELETE FROM intelligence_log 
            WHERE teams ILIKE '%Colorado St%' 
            AND teams ILIKE '%San Diego St%'
            AND selection ILIKE '%Under 139.5%'
            AND abs(odds - 1.87) < 0.01
        """)
        c = cur.rowcount
        conn.commit()
        print(f"   ✅ Deleted {c} duplicate rows.")
        
    except Exception as e:
        print(f"❌ [MIGRATION] Failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
