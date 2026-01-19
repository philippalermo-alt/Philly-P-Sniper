"""
Smart Staking System

Adjusts stake recommendations based on historical performance
by sport and edge range.
"""

import pandas as pd
from datetime import datetime, timedelta
from database import get_db
from config import Config
from utils import log

def get_performance_multipliers(days_back=60, min_bets=10):
    """
    Calculate performance-based multipliers for different sports and edge ranges.

    Args:
        days_back: Number of days of history to analyze
        min_bets: Minimum number of bets required for a category to be considered

    Returns:
        dict: Nested dictionary with multipliers by sport and edge bucket
    """
    conn = get_db()
    if not conn:
        log("SMART_STAKE", "No database connection, using default multipliers")
        return {}

    try:
        cur = conn.cursor()

        # Get settled bets from the last N days
        start_date = datetime.now() - timedelta(days=days_back)

        query = """
            SELECT sport, edge, odds, stake, outcome
            FROM intelligence_log
            WHERE outcome IN ('WON', 'LOST', 'PUSH')
            AND kickoff >= %s
            AND edge IS NOT NULL
            AND stake > 0
        """

        cur.execute(query, (start_date,))
        rows = cur.fetchall()

        if not rows:
            log("SMART_STAKE", "No historical data found, using default multipliers")
            return {}

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['sport', 'edge', 'odds', 'stake', 'outcome'])

        # Define edge buckets
        df['edge_bucket'] = pd.cut(
            df['edge'],
            bins=[-1, 0.03, 0.06, 0.10, 1.0],
            labels=['0-3%', '3-6%', '6-10%', '10%+']
        )

        # Calculate profit for each bet
        def calc_profit(row):
            if row['outcome'] == 'WON':
                return row['stake'] * (row['odds'] - 1)
            elif row['outcome'] == 'LOST':
                return -row['stake']
            else:  # PUSH
                return 0

        df['profit'] = df.apply(calc_profit, axis=1)

        multipliers = {}

        # Calculate multipliers by sport and edge bucket
        sports = df['sport'].unique()

        for sport in sports:
            sport_df = df[df['sport'] == sport]
            multipliers[sport] = {}

            for bucket in ['0-3%', '3-6%', '6-10%', '10%+']:
                bucket_df = sport_df[sport_df['edge_bucket'] == bucket]

                if len(bucket_df) < min_bets:
                    # Not enough data, use neutral multiplier
                    multipliers[sport][bucket] = 1.0
                    continue

                # Calculate ROI
                total_staked = bucket_df['stake'].sum()
                total_profit = bucket_df['profit'].sum()
                roi = (total_profit / total_staked) if total_staked > 0 else 0

                # Calculate multiplier based on ROI
                # Positive ROI = increase stake (max 2x)
                # Negative ROI = decrease stake (min 0.25x)
                if roi > 0.15:  # Excellent performance
                    multiplier = 2.0
                elif roi > 0.05:  # Good performance
                    multiplier = 1.5
                elif roi > 0:  # Slight edge
                    multiplier = 1.2
                elif roi > -0.05:  # Breakeven-ish
                    multiplier = 0.8
                elif roi > -0.15:  # Losing
                    multiplier = 0.5
                else:  # Badly losing
                    multiplier = 0.25

                multipliers[sport][bucket] = round(multiplier, 2)

                log("SMART_STAKE", f"{sport} {bucket}: {len(bucket_df)} bets, ROI={roi:.1%}, multiplier={multiplier:.2f}")

        return multipliers

    except Exception as e:
        log("ERROR", f"Smart staking error: {e}")
        return {}
    finally:
        if conn:
            cur.close()
            conn.close()


def calculate_smart_stake(base_stake, sport, edge, multipliers=None):
    """
    Calculate adjusted stake based on historical performance.

    Args:
        base_stake: Base Kelly stake calculation
        sport: Sport category
        edge: Edge value (decimal, e.g., 0.05 for 5%)
        multipliers: Pre-calculated multipliers dict (optional)

    Returns:
        float: Adjusted stake amount
    """
    if not multipliers:
        multipliers = get_performance_multipliers()

    if not multipliers or sport not in multipliers:
        # No data for this sport, use base stake
        return base_stake

    # Determine edge bucket
    if edge < 0.03:
        bucket = '0-3%'
    elif edge < 0.06:
        bucket = '3-6%'
    elif edge < 0.10:
        bucket = '6-10%'
    else:
        bucket = '10%+'

    multiplier = multipliers[sport].get(bucket, 1.0)

    adjusted_stake = base_stake * multiplier

    # Respect maximum stake limits
    max_stake = Config.BANKROLL * Config.MAX_STAKE_PCT

    return min(adjusted_stake, max_stake)


def print_multiplier_report(multipliers):
    """Print formatted report of current multipliers."""
    if not multipliers:
        print("No multiplier data available")
        return

    print("\n" + "="*60)
    print("📊 SMART STAKING MULTIPLIERS")
    print("="*60)

    for sport in sorted(multipliers.keys()):
        print(f"\n{sport}:")
        for bucket in ['0-3%', '3-6%', '6-10%', '10%+']:
            multiplier = multipliers[sport].get(bucket, 1.0)

            if multiplier >= 1.5:
                indicator = "🔥 INCREASE"
            elif multiplier >= 1.0:
                indicator = "✅ NORMAL"
            elif multiplier >= 0.5:
                indicator = "⚠️  REDUCE"
            else:
                indicator = "❌ MINIMIZE"

            print(f"  {bucket:8} {indicator:15} {multiplier:.2f}x")

    print("\n" + "="*60)


if __name__ == "__main__":
    # Test the module
    multipliers = get_performance_multipliers()
    print_multiplier_report(multipliers)
