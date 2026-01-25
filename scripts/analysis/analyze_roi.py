
import pandas as pd
from database import get_db
from datetime import datetime

def analyze_roi():
    conn = get_db()
    if not conn:
        print("DB Connection Failed")
        return

    # Fetch Settled Bets
    query = """
        SELECT sport, edge, odds, stake, outcome, user_bet
        FROM intelligence_log
        WHERE outcome IN ('WON', 'LOST', 'PUSH')
        AND user_bet = TRUE
    """
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("No settled bets found.")
        return

    # Clean Data
    df['edge_pct'] = pd.to_numeric(df['edge'], errors='coerce') * 100.0
    df['stake'] = pd.to_numeric(df['stake'], errors='coerce').fillna(0.0)
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    
    # Calculate Profit
    def get_profit(row):
        if row['outcome'] == 'WON':
            return row['stake'] * (row['odds'] - 1)
        elif row['outcome'] == 'LOST':
            return -row['stake']
        return 0.0

    df['profit'] = df.apply(get_profit, axis=1)

    # Buckets
    bins = [0, 3, 6, 10, 100]
    labels = ['0-3%', '3-6%', '6-10%', '10%+']
    df['bucket'] = pd.cut(df['edge_pct'], bins=bins, labels=labels, right=False)

    # Aggregation
    report = df.groupby(['sport', 'bucket']).agg(
        Bets=('outcome', 'count'),
        Stake=('stake', 'sum'),
        Profit=('profit', 'sum'),
        Wins=('outcome', lambda x: (x=='WON').sum())
    )
    
    report['ROI'] = (report['Profit'] / report['Stake']) * 100
    report['Win_Rate'] = (report['Wins'] / report['Bets']) * 100

    print("### ROI Analysis Report")
    print(report.dropna(subset=['Bets']).to_markdown())

    print("\n\n### Sport Summary")
    sport_summary = df.groupby('sport').agg(
        Bets=('outcome', 'count'),
        ROI=('profit', lambda x: x.sum() / df.loc[x.index, 'stake'].sum() * 100)
    )
    print(sport_summary.to_markdown())

if __name__ == "__main__":
    analyze_roi()
