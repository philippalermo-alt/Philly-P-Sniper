"""
Historical Performance Backtesting Module

Analyzes past performance to evaluate model accuracy, profitability,
and identify areas for improvement.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import get_db
from utils import log

def run_backtest(start_date=None, end_date=None, sport=None, min_edge=None):
    """
    Run a comprehensive backtest on historical data.

    Args:
        start_date: Start date for backtest (default: 30 days ago)
        end_date: End date for backtest (default: today)
        sport: Filter by sport (optional)
        min_edge: Filter by minimum edge (optional)

    Returns:
        dict: Backtest results with performance metrics
    """
    conn = get_db()
    if not conn:
        return {}

    try:
        # Default date range
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        log("BACKTEST", f"Running backtest from {start_date.date()} to {end_date.date()}")

        cur = conn.cursor()

        # Build query
        query = """
            SELECT
                event_id, timestamp, kickoff, sport, teams, selection,
                odds, true_prob, edge, stake, outcome, closing_odds,
                user_bet, user_odds, user_stake, sharp_score,
                ticket_pct, money_pct
            FROM intelligence_log
            WHERE outcome IN ('WON', 'LOST', 'PUSH')
            AND kickoff BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if sport:
            query += " AND sport = %s"
            params.append(sport)

        if min_edge is not None:
            query += " AND edge >= %s"
            params.append(min_edge)

        query += " ORDER BY kickoff"

        cur.execute(query, params)
        rows = cur.fetchall()

        if not rows:
            log("BACKTEST", "No completed bets found in date range")
            return {}

        # Convert to DataFrame for analysis
        df = pd.DataFrame(rows, columns=[
            'event_id', 'timestamp', 'kickoff', 'sport', 'teams', 'selection',
            'odds', 'true_prob', 'edge', 'stake', 'outcome', 'closing_odds',
            'user_bet', 'user_odds', 'user_stake', 'sharp_score',
            'ticket_pct', 'money_pct'
        ])

        log("BACKTEST", f"Analyzing {len(df)} settled bets")

        # Calculate metrics
        results = calculate_backtest_metrics(df)

        # Add calibration analysis
        results['calibration'] = analyze_calibration(df)

        # Add edge analysis
        results['edge_analysis'] = analyze_by_edge_bucket(df)

        # Add sport breakdown
        results['by_sport'] = analyze_by_sport(df)

        # Add sharp score analysis
        results['sharp_analysis'] = analyze_by_sharp_score(df)

        # Add CLV analysis
        results['clv_analysis'] = analyze_clv(df)

        # Add time-based analysis
        results['time_series'] = analyze_time_series(df)

        return results

    except Exception as e:
        log("ERROR", f"Backtest error: {e}")
        return {}
    finally:
        cur.close()
        conn.close()

def calculate_backtest_metrics(df):
    """Calculate overall performance metrics."""
    total_bets = len(df)
    wins = len(df[df['outcome'] == 'WON'])
    losses = len(df[df['outcome'] == 'LOST'])
    pushes = len(df[df['outcome'] == 'PUSH'])

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    # Calculate profit/loss
    df['result'] = df.apply(calculate_bet_result, axis=1)
    total_profit = df['result'].sum()
    total_staked = df['stake'].sum()
    roi = (total_profit / total_staked * 100) if total_staked > 0 else 0

    # Calculate expected value
    df['expected_return'] = df['stake'] * df['edge']
    expected_profit = df['expected_return'].sum()
    expected_roi = (expected_profit / total_staked * 100) if total_staked > 0 else 0

    # Longest winning/losing streaks
    df['win'] = (df['outcome'] == 'WON').astype(int)
    df['loss'] = (df['outcome'] == 'LOST').astype(int)

    max_win_streak = calculate_max_streak(df['win'])
    max_loss_streak = calculate_max_streak(df['loss'])

    # Sharpe ratio (risk-adjusted returns)
    if len(df['result']) > 1:
        sharpe = (df['result'].mean() / df['result'].std()) * np.sqrt(len(df)) if df['result'].std() > 0 else 0
    else:
        sharpe = 0

    return {
        'total_bets': total_bets,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'win_rate': round(win_rate, 2),
        'total_profit': round(total_profit, 2),
        'total_staked': round(total_staked, 2),
        'roi': round(roi, 2),
        'expected_profit': round(expected_profit, 2),
        'expected_roi': round(expected_roi, 2),
        'max_win_streak': max_win_streak,
        'max_loss_streak': max_loss_streak,
        'sharpe_ratio': round(sharpe, 2)
    }

def calculate_bet_result(row):
    """Calculate profit/loss for a single bet."""
    if row['outcome'] == 'WON':
        return row['stake'] * (row['odds'] - 1)
    elif row['outcome'] == 'LOST':
        return -row['stake']
    else:  # PUSH
        return 0

def calculate_max_streak(series):
    """Calculate maximum consecutive streak in binary series."""
    if len(series) == 0:
        return 0

    max_streak = 0
    current_streak = 0

    for val in series:
        if val == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak

def analyze_calibration(df):
    """Analyze how well predicted probabilities match actual outcomes."""
    # Group by predicted probability buckets
    df['prob_bucket'] = pd.cut(df['true_prob'], bins=[0, 0.4, 0.5, 0.6, 0.7, 1.0],
                                 labels=['<40%', '40-50%', '50-60%', '60-70%', '70%+'])

    calibration = []

    for bucket in df['prob_bucket'].unique():
        if pd.isna(bucket):
            continue

        bucket_df = df[df['prob_bucket'] == bucket]
        actual_win_rate = len(bucket_df[bucket_df['outcome'] == 'WON']) / len(bucket_df[bucket_df['outcome'].isin(['WON', 'LOST'])]) if len(bucket_df[bucket_df['outcome'].isin(['WON', 'LOST'])]) > 0 else 0
        predicted_prob = bucket_df['true_prob'].mean()

        calibration.append({
            'bucket': str(bucket),
            'count': len(bucket_df),
            'predicted_prob': round(predicted_prob, 3),
            'actual_win_rate': round(actual_win_rate, 3),
            'calibration_error': round(abs(predicted_prob - actual_win_rate), 3)
        })

    return sorted(calibration, key=lambda x: x['predicted_prob'])

def analyze_by_edge_bucket(df):
    """Analyze performance by edge size."""
    df['edge_bucket'] = pd.cut(df['edge'], bins=[-1, 0, 0.03, 0.06, 0.10, 1.0],
                                 labels=['<0%', '0-3%', '3-6%', '6-10%', '10%+'])

    edge_analysis = []

    for bucket in df['edge_bucket'].unique():
        if pd.isna(bucket):
            continue

        bucket_df = df[df['edge_bucket'] == bucket]
        wins = len(bucket_df[bucket_df['outcome'] == 'WON'])
        losses = len(bucket_df[bucket_df['outcome'] == 'LOST'])
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        bucket_df['result'] = bucket_df.apply(calculate_bet_result, axis=1)
        profit = bucket_df['result'].sum()
        staked = bucket_df['stake'].sum()
        roi = (profit / staked * 100) if staked > 0 else 0

        edge_analysis.append({
            'edge_bucket': str(bucket),
            'count': len(bucket_df),
            'win_rate': round(win_rate, 2),
            'profit': round(profit, 2),
            'roi': round(roi, 2),
            'avg_edge': round(bucket_df['edge'].mean() * 100, 2)
        })

    return sorted(edge_analysis, key=lambda x: x['avg_edge'])

def analyze_by_sport(df):
    """Analyze performance breakdown by sport."""
    sport_analysis = []

    for sport in df['sport'].unique():
        sport_df = df[df['sport'] == sport]
        wins = len(sport_df[sport_df['outcome'] == 'WON'])
        losses = len(sport_df[sport_df['outcome'] == 'LOST'])
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        sport_df['result'] = sport_df.apply(calculate_bet_result, axis=1)
        profit = sport_df['result'].sum()
        staked = sport_df['stake'].sum()
        roi = (profit / staked * 100) if staked > 0 else 0

        sport_analysis.append({
            'sport': sport,
            'count': len(sport_df),
            'win_rate': round(win_rate, 2),
            'profit': round(profit, 2),
            'roi': round(roi, 2)
        })

    return sorted(sport_analysis, key=lambda x: x['roi'], reverse=True)

def analyze_by_sharp_score(df):
    """Analyze performance by sharp score."""
    df_with_sharp = df[df['sharp_score'].notna()]

    if len(df_with_sharp) == 0:
        return []

    df_with_sharp['sharp_bucket'] = pd.cut(df_with_sharp['sharp_score'],
                                             bins=[0, 25, 50, 75, 100],
                                             labels=['0-25', '25-50', '50-75', '75-100'])

    sharp_analysis = []

    for bucket in df_with_sharp['sharp_bucket'].unique():
        if pd.isna(bucket):
            continue

        bucket_df = df_with_sharp[df_with_sharp['sharp_bucket'] == bucket]
        wins = len(bucket_df[bucket_df['outcome'] == 'WON'])
        losses = len(bucket_df[bucket_df['outcome'] == 'LOST'])
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        bucket_df['result'] = bucket_df.apply(calculate_bet_result, axis=1)
        profit = bucket_df['result'].sum()
        staked = bucket_df['stake'].sum()
        roi = (profit / staked * 100) if staked > 0 else 0

        sharp_analysis.append({
            'sharp_bucket': str(bucket),
            'count': len(bucket_df),
            'win_rate': round(win_rate, 2),
            'profit': round(profit, 2),
            'roi': round(roi, 2)
        })

    return sorted(sharp_analysis, key=lambda x: x['sharp_bucket'])

def analyze_clv(df):
    """Analyze Closing Line Value performance."""
    df_with_clv = df[df['closing_odds'].notna() & (df['closing_odds'] != df['odds'])]

    if len(df_with_clv) == 0:
        return {}

    df_with_clv['clv'] = ((df_with_clv['odds'] - df_with_clv['closing_odds']) / df_with_clv['odds']) * 100

    positive_clv = df_with_clv[df_with_clv['clv'] > 0]
    negative_clv = df_with_clv[df_with_clv['clv'] < 0]

    def calc_roi(subset):
        if len(subset) == 0:
            return 0
        subset['result'] = subset.apply(calculate_bet_result, axis=1)
        profit = subset['result'].sum()
        staked = subset['stake'].sum()
        return (profit / staked * 100) if staked > 0 else 0

    return {
        'total_with_clv': len(df_with_clv),
        'avg_clv': round(df_with_clv['clv'].mean(), 2),
        'positive_clv_count': len(positive_clv),
        'positive_clv_pct': round(len(positive_clv) / len(df_with_clv) * 100, 2) if len(df_with_clv) > 0 else 0,
        'positive_clv_roi': round(calc_roi(positive_clv), 2),
        'negative_clv_roi': round(calc_roi(negative_clv), 2)
    }

def analyze_time_series(df):
    """Analyze performance over time (rolling metrics)."""
    df = df.sort_values('kickoff')
    df['result'] = df.apply(calculate_bet_result, axis=1)

    # Calculate cumulative metrics
    df['cumulative_profit'] = df['result'].cumsum()
    df['cumulative_staked'] = df['stake'].cumsum()
    df['rolling_roi'] = (df['cumulative_profit'] / df['cumulative_staked'] * 100).where(df['cumulative_staked'] > 0, 0)

    # Calculate 20-bet rolling win rate
    df['win'] = (df['outcome'] == 'WON').astype(int)
    df['rolling_win_rate'] = df['win'].rolling(window=20, min_periods=1).mean() * 100

    return {
        'final_profit': round(df['cumulative_profit'].iloc[-1], 2),
        'final_roi': round(df['rolling_roi'].iloc[-1], 2),
        'peak_profit': round(df['cumulative_profit'].max(), 2),
        'max_drawdown': round(df['cumulative_profit'].max() - df['cumulative_profit'].min(), 2),
        'current_win_rate': round(df['rolling_win_rate'].iloc[-1], 2)
    }

def print_backtest_report(results):
    """Print formatted backtest report."""
    print("\n" + "="*80)
    print("📊 BACKTEST RESULTS")
    print("="*80)

    # Overall metrics
    print("\n🎯 Overall Performance:")
    print(f"  Total Bets: {results['total_bets']}")
    print(f"  Record: {results['wins']}W - {results['losses']}L - {results['pushes']}P")
    print(f"  Win Rate: {results['win_rate']}%")
    print(f"  Profit: ${results['total_profit']:.2f} (Staked: ${results['total_staked']:.2f})")
    print(f"  ROI: {results['roi']}%")
    print(f"  Expected ROI: {results['expected_roi']}%")
    print(f"  Sharpe Ratio: {results['sharpe_ratio']}")
    print(f"  Max Win Streak: {results['max_win_streak']}")
    print(f"  Max Loss Streak: {results['max_loss_streak']}")

    # Calibration
    if results.get('calibration'):
        print("\n📈 Calibration Analysis:")
        for cal in results['calibration']:
            print(f"  {cal['bucket']}: Predicted {cal['predicted_prob']:.1%}, Actual {cal['actual_win_rate']:.1%} ({cal['count']} bets)")

    # Edge analysis
    if results.get('edge_analysis'):
        print("\n💰 Performance by Edge:")
        for edge in results['edge_analysis']:
            print(f"  {edge['edge_bucket']}: {edge['count']} bets, {edge['win_rate']}% win rate, {edge['roi']}% ROI")

    # Sport breakdown
    if results.get('by_sport'):
        print("\n🏀 Performance by Sport:")
        for sport in results['by_sport']:
            print(f"  {sport['sport']}: {sport['count']} bets, {sport['win_rate']}% win rate, {sport['roi']}% ROI, ${sport['profit']:.2f} profit")

    # CLV analysis
    if results.get('clv_analysis') and results['clv_analysis']:
        clv = results['clv_analysis']
        print("\n📉 Closing Line Value (CLV) Analysis:")
        print(f"  Avg CLV: {clv['avg_clv']}%")
        print(f"  Positive CLV: {clv['positive_clv_count']}/{clv['total_with_clv']} ({clv['positive_clv_pct']}%)")
        print(f"  Positive CLV ROI: {clv['positive_clv_roi']}%")
        print(f"  Negative CLV ROI: {clv['negative_clv_roi']}%")

    print("\n" + "="*80)
