from database import get_db

def clear_pending():
    conn = get_db()
    cur = conn.cursor()
    
    # Reset pending bets for NCAAB
    # Or actually clear 'model' triggers to let them re-fire?
    # User said "Clear ghost bets", implying pending bets that are clogging the system or are now invalid.
    # Safe approach: DELETE from logic where outcome is NULL (pending).
    # Then `fetch_scores` will re-scan and re-insert if valid.
    
    # We only clear PENDING bets.
    cur.execute("DELETE FROM intelligence_log WHERE outcome IS NULL AND sport='NCAAB'")
    deleted = cur.rowcount
    
    conn.commit()
    print(f"🧹 Cleared {deleted} pending NCAAB bets.")

if __name__ == "__main__":
    clear_pending()
