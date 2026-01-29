"""
Closing Line Value (CLV) tracking and analysis.

This module fetches closing odds before games start and calculates CLV,
which is a key metric for measuring betting skill over time.
"""

import requests
from datetime import datetime, timezone, timedelta
from config import Config
from db.connection import get_db, safe_execute
from utils import log

def fetch_closing_odds():
    """
    Fetch closing odds for pending bets that are about to start.
    Updates the closing_odds field in the database.

    CLV (Closing Line Value) is the difference between the odds you got
    and the closing odds. Positive CLV indicates you beat the market.
    """
    log("CLV", "Fetching closing odds for upcoming games...")

    conn = get_db()
    if not conn:
        return

    cur = conn.cursor()

    try:
        # OPTIMIZATION: Only fetch if kickoff is IMMINENT (Next 70 mins)
        # This prevents wasting API credits checking lines 6 hours away.
        # Assumes Hourly Scheduler.
        cur.execute("""
            SELECT event_id, sport, teams, selection, odds, kickoff
            FROM intelligence_log
            WHERE outcome = 'PENDING'
            AND kickoff BETWEEN NOW() AND NOW() + INTERVAL '70 minutes'
        """)

        pending = cur.fetchall()

        if not pending:
            log("CLV", "No pending bets approaching kickoff")
            return

        log("CLV", f"Found {len(pending)} bets to update with closing odds")

        sport_map = {
            'NBA': 'basketball_nba',
            'NCAAB': 'basketball_ncaab',
            'NFL': 'americanfootball_nfl',
            'NHL': 'icehockey_nhl',
            'SOCCER': 'soccer_epl'
        }

        updated = 0

        for event_id, sport, teams, selection, opening_odds, kickoff in pending:
            league = sport_map.get(sport)
            if not league:
                continue

            # Extract base event ID (before the underscore)
            base_event_id = event_id.split('_')[0]

            try:
                # Fetch current odds for this event
                url = f"https://api.the-odds-api.com/v4/sports/{league}/events/{base_event_id}/odds?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.MAIN_MARKETS},{Config.EXOTIC_MARKETS}"
                res = requests.get(url, timeout=10).json()

                if not isinstance(res, dict) or 'bookmakers' not in res:
                    continue

                # Find the matching selection
                closing_odds = find_matching_odds(res, selection, teams)

                if closing_odds:
                    # Calculate CLV (Current)
                    clv = calculate_clv(opening_odds, closing_odds)

                    # Always update to the latest line we see
                    safe_execute(
                        cur,
                        "UPDATE intelligence_log SET closing_odds = %s WHERE event_id = %s",
                        (closing_odds, event_id)
                    )

                    updated += 1
                    log("CLV", f"Updated {event_id}: Open={opening_odds:.2f} → Close={closing_odds:.2f} (CLV: {clv:+.1f}%)")

            except Exception as e:
                log("ERROR", f"Failed to fetch closing odds for {event_id}: {e}")
                continue

        conn.commit()

        if updated > 0:
            log("CLV", f"Successfully updated {updated} closing odds")

    except Exception as e:
        log("ERROR", f"Error in fetch_closing_odds: {e}")
    finally:
        cur.close()
        conn.close()

def find_matching_odds(odds_data, selection, teams):
    """
    Find the odds for a specific selection from the odds API response.

    Args:
        odds_data: API response with bookmakers and markets
        selection: Selection string (e.g., "Lakers ML", "Lakers +5.0")
        teams: Teams string (e.g., "Lakers @ Warriors")

    Returns:
        float: Closing odds or None
    """
    # Get preferred book or first available
    bookie = None
    for b in odds_data.get('bookmakers', []):
        if b['key'] in Config.PREFERRED_BOOKS:
            bookie = b
            break

    if not bookie and odds_data.get('bookmakers'):
        bookie = odds_data['bookmakers'][0]

    if not bookie:
        return None

    # Parse selection to determine market and outcome
    for market in bookie.get('markets', []):
        for outcome in market.get('outcomes', []):
            # Match moneylines
            if ' ML' in selection:
                if market['key'] in ['h2h', 'h2h_h1']:
                    team_name = selection.replace(' ML', '').replace('1H', '').replace('1st Half', '').strip()
                    if team_name.lower() in outcome['name'].lower() or outcome['name'].lower() in team_name.lower():
                        return outcome.get('price')
                    if 'Draw' in selection and ('Draw' in outcome['name'] or 'Tie' in outcome['name']):
                        return outcome.get('price')

            # Match spreads
            elif '+' in selection or '-' in selection:
                if market['key'] in ['spreads', 'spreads_h1']:
                    parts = selection.rsplit(' ', 1)
                    if len(parts) == 2:
                        team_name = parts[0].replace('1H', '').replace('1st Half', '').strip()
                        spread = float(parts[1])
                        if (team_name.lower() in outcome['name'].lower() or
                            outcome['name'].lower() in team_name.lower()):
                            if abs(outcome.get('point', 0) - spread) < 0.1:
                                return outcome.get('price')

            # Match totals
            elif 'Over' in selection or 'Under' in selection:
                if market['key'] in ['totals', 'totals_h1']:
                    try:
                        line = float(selection.split()[-1])
                        if abs(outcome.get('point', 0) - line) < 0.1:
                            if ('Over' in selection and outcome['name'] == 'Over') or \
                               ('Under' in selection and outcome['name'] == 'Under'):
                                return outcome.get('price')
                    except:
                        pass

    return None

def calculate_clv(opening_odds, closing_odds):
    """
    Calculate Closing Line Value (CLV) as a percentage.

    CLV = (closing_implied_prob - opening_implied_prob) / opening_implied_prob * 100

    Positive CLV means you beat the closing line (good).
    Negative CLV means the line moved against you (bad).

    Args:
        opening_odds: Decimal odds when bet was placed
        closing_odds: Decimal odds at game time

    Returns:
        float: CLV percentage
    """
    if not opening_odds or not closing_odds or opening_odds == 0:
        return 0.0

    opening_implied = 1 / opening_odds
    closing_implied = 1 / closing_odds

    # CLV is the improvement in your position
    # If closing odds are lower, closing_implied is higher, meaning sharper money came in on your side
    clv = ((opening_odds - closing_odds) / opening_odds) * 100

    return clv

def get_clv_stats(sport=None, days=30):
    """
    Get CLV statistics for analysis.

    Args:
        sport: Filter by sport (optional)
        days: Number of days to look back

    Returns:
        dict: CLV statistics
    """
    conn = get_db()
    if not conn:
        return {}

    try:
        cur = conn.cursor()

        query = """
            SELECT
                COUNT(*) as total_bets,
                AVG((odds - closing_odds) / odds * 100) as avg_clv,
                SUM(CASE WHEN closing_odds < odds THEN 1 ELSE 0 END) as positive_clv_count,
                SUM(CASE WHEN outcome = 'WON' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN outcome = 'LOST' THEN 1 ELSE 0 END) as losses
            FROM intelligence_log
            WHERE closing_odds IS NOT NULL
            AND closing_odds != odds
            AND timestamp > NOW() - INTERVAL '%s days'
        """

        params = [days]

        if sport:
            query += " AND sport = %s"
            params.append(sport)

        cur.execute(query, params)
        row = cur.fetchone()

        if row:
            total, avg_clv, pos_clv, wins, losses = row
            return {
                'total_bets': total or 0,
                'avg_clv': float(avg_clv or 0),
                'positive_clv_pct': (pos_clv / total * 100) if total else 0,
                'win_rate': (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0,
                'wins': wins or 0,
                'losses': losses or 0
            }

        return {}

    except Exception as e:
        log("ERROR", f"Error getting CLV stats: {e}")
        return {}
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    # Ensure config is loaded
    from dotenv import load_dotenv
    load_dotenv()
    fetch_closing_odds()
