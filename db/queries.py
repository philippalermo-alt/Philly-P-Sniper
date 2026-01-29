"""Named database queries and data access layer."""

import pandas as pd
from datetime import datetime

# --- SQL Template Constants ---

PENDING_OPPORTUNITIES = """
    SELECT 
        event_id, timestamp, kickoff, sport, teams, selection,
        odds, true_prob, edge, stake, outcome, user_bet, user_odds, user_stake,
        sharp_score, ticket_pct, money_pct, trigger_type
    FROM intelligence_log 
    WHERE outcome = 'PENDING' 
    AND (timestamp >= NOW() - INTERVAL '48 HOURS' OR user_bet = TRUE) 
    ORDER BY kickoff ASC 
    LIMIT %(limit)s
"""

SETTLED_BETS = """
    SELECT 
        event_id, timestamp, kickoff, sport, teams, selection,
        odds, true_prob, edge, stake, outcome, user_bet, user_odds, user_stake,
        sharp_score, ticket_pct, money_pct, trigger_type
    FROM intelligence_log 
    WHERE outcome IN ('WON', 'LOST', 'PUSH') 
    ORDER BY kickoff DESC
"""

DISTINCT_SPORTS = "SELECT DISTINCT sport FROM intelligence_log"

UPDATE_USER_BET = """
    UPDATE intelligence_log 
    SET user_bet = TRUE, user_odds = %s, user_stake = %s 
    WHERE event_id = %s
"""

CANCEL_USER_BET = "UPDATE intelligence_log SET user_bet = FALSE WHERE event_id = %s"

CHECK_EVENT_EXISTS = "SELECT event_id FROM intelligence_log WHERE event_id = %s"

INSERT_PARLAY = """
    INSERT INTO intelligence_log 
    (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, user_bet, user_odds, user_stake, outcome)
    VALUES (%s, NOW(), NOW(), 'PARLAY', 'Edge Triple', %s, %s, 0, 0, %s, TRUE, %s, %s, 'PENDING')
"""


# --- Data Access Functions ---

def fetch_pending_opportunities(conn, limit: int = 500) -> pd.DataFrame:
    """Fetch pending betting opportunities."""
    if not conn: return pd.DataFrame()
    return pd.read_sql(PENDING_OPPORTUNITIES, conn, params={'limit': limit})

def fetch_settled_bets(conn) -> pd.DataFrame:
    """Fetch all settled bets."""
    if not conn: return pd.DataFrame()
    return pd.read_sql(SETTLED_BETS, conn)

def fetch_distinct_sports(conn) -> list:
    """Fetch list of unique sports found in the logs."""
    if not conn: return []
    try:
        df = pd.read_sql(DISTINCT_SPORTS, conn)
        return df['sport'].tolist()
    except:
        return []

def update_user_bet(conn, event_id: str, odds: float, stake: float) -> int:
    """
    Mark a bet as tracked/placed by the user.
    Returns number of rows affected.
    """
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute(UPDATE_USER_BET, (odds, stake, str(event_id)))
        rows = cur.rowcount
        conn.commit()
        cur.close()
        return rows
    except Exception as e:
        print(f"❌ DB Update Error: {e}")
        conn.rollback()
        raise e

def cancel_user_bet(conn, event_id: str) -> int:
    """
    Untrack a bet (set user_bet = False).
    Returns number of rows affected.
    """
    if not conn: return 0
    try:
        cur = conn.cursor()
        cur.execute(CANCEL_USER_BET, (str(event_id),))
        rows = cur.rowcount
        conn.commit()
        cur.close()
        return rows
    except Exception as e:
        print(f"❌ DB Cancel Error: {e}")
        conn.rollback()
        raise e

def save_parlay(conn, event_id: str, selection_text: str, odds: float, stake: float):
    """Save a parlay bet to the database."""
    if not conn: return
    try:
        cur = conn.cursor()
        # Check existence
        cur.execute(CHECK_EVENT_EXISTS, (event_id,))
        if cur.fetchone():
            return # Already exists
            
        cur.execute(INSERT_PARLAY, (event_id, selection_text, odds, stake, odds, stake))
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"❌ DB Parlay Error: {e}")
        conn.rollback()
        raise e
