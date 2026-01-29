import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.connection import get_db, safe_execute
from utils.logging import log

def migrate():
    log("INFO", "🚀 Starting Schema Migration: Single Source of Truth Columns")
    conn = get_db()
    if not conn:
        log("ERROR", "Could not connect to DB")
        return

    try:
        cur = conn.cursor()

        # 1. Add Columns if not exist
        log("INFO", "Step 1: Adding Columns (settled_at, net_units)...")
        queries = [
            "ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS settled_at TIMESTAMP;",
            "ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS net_units FLOAT DEFAULT 0.0;",
            "ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS accepted BOOLEAN DEFAULT TRUE;"
        ]

        for q in queries:
            try:
                cur.execute(q)
                log("INFO", f"Executed: {q}")
            except Exception as e:
                log("WARNING", f"Query skipped/failed ({q}): {e}")
                conn.rollback()
            else:
                conn.commit()

        # 2. Backfill (Heuristic)
        # For existing WON/LOST bets with NULL settled_at, set it to kickoff + 3 hours roughly?
        # Actually, for the recap to work "for yesterday", we need them to be in the yesterday window.
        # Let's set settled_at = generated_at (if exists) or kickoff + 2 hours.
        # And calculate net_units.
        
        log("INFO", "Step 2: Backfilling Data...")
        
        # Calculate Net Units first
        # Won
        cur.execute("""
            UPDATE intelligence_log
            SET net_units = (COALESCE(stake, 1.0) * (odds - 1.0))
            WHERE outcome = 'WON' AND net_units = 0.0
        """)
        log("INFO", f"Backfilled Net Units (WON): {cur.rowcount} rows")
        
        # Lost
        cur.execute("""
            UPDATE intelligence_log
            SET net_units = -COALESCE(stake, 1.0)
            WHERE outcome = 'LOST' AND net_units = 0.0
        """)
        log("INFO", f"Backfilled Net Units (LOST): {cur.rowcount} rows")
        
        # Push
        cur.execute("""
            UPDATE intelligence_log
            SET net_units = 0.0
            WHERE outcome = 'PUSH'
        """)
        
        # Settled At
        # Backfill to kickoff + 2.5 hours (approx game end)
        cur.execute("""
            UPDATE intelligence_log
            SET settled_at = kickoff + INTERVAL '150 minutes'
            WHERE outcome IN ('WON', 'LOST', 'PUSH') AND settled_at IS NULL
        """)
        log("INFO", f"Backfilled settled_at: {cur.rowcount} rows")

        conn.commit()
        log("INFO", "✅ Migration Complete.")

    except Exception as e:
        log("ERROR", f"Migration Failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
