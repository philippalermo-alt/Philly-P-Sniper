
import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def analyze_buckets():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL missing")
        return

    # Connect to DB (No SSL for local docker exec)
    conn = psycopg2.connect(db_url)

    sports_to_analyze = ['NCAAB', 'NBA']
    
    for sport in sports_to_analyze:
        print(f"\n🏀 **Analyzing {sport}**")
        print("=" * 65)
        
        # Filter dataframe in memory or re-query? Re-querying is cleaner for this script structure.
        sport_query = f"""
            SELECT 
                sport,
                selection,
                edge,
                sharp_score,
                outcome,
                odds
            FROM intelligence_log
            WHERE outcome IN ('WON', 'LOST')
              AND sharp_score IS NOT NULL
              AND sport = '{sport}'
              AND edge >= 0.10
        """
        
        df = pd.read_sql(sport_query, conn)
        
        if df.empty:
            print(f"⚠️ No bets found for {sport}")
            continue

        # Bucketize
        bins = [0, 25, 50, 75, 100]
        labels = ['0-25', '26-50', '51-75', '76-100']
        df['bucket'] = pd.cut(df['sharp_score'], bins=bins, labels=labels, include_lowest=True)
        
        print(f"{'Bucket':<10} | {'Bets':<6} | {'Profit':<10} | {'ROI':<8} | {'Win Rate':<8}")
        print("-" * 65)

        for bucket in labels:
            subset = df[df['bucket'] == bucket].copy()
            
            if subset.empty:
                print(f"{bucket:<10} | {0:<6} | {0.0:>8.2f}u | {'--':>7} | {'--':>7}")
                continue
                
            # Calculate Stats (Flat 1u Stake)
            subset['units_won'] = subset.apply(lambda x: (x['odds'] - 1) if x['outcome'] == 'WON' else -1, axis=1)
            profit = subset['units_won'].sum()
            count = len(subset)
            roi = (profit / count) * 100
            wins = len(subset[subset['outcome'] == 'WON'])
            wr = (wins / count) * 100
            
            print(f"{bucket:<10} | {count:<6} | {profit:>8.2f}u | {roi:>7.1f}% | {wr:>7.1f}%")
        print("-" * 65)

    conn.close()

if __name__ == "__main__":
    analyze_buckets()
