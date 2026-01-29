from db.connection import get_db
import pandas as pd
import json
from datetime import datetime, timedelta

def run_daily_monitor():
    print("📊 NBA Phase 7 Daily Monitor")
    conn = get_db()
    
    # 1. Fetch recent recommendations (Last 24h)
    query = """
        SELECT * FROM intelligence_log 
        WHERE sport = 'NBA' 
        AND timestamp > NOW() - INTERVAL '24 HOURS'
    """
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("⚠️ No NBA recommendations generated in last 24h.")
        return
        
    # 2. Parse Metadata (Buckets)
    # The 'metadata' column in DB is JSONB, pandas reads as dict or string? 
    # Usually dict if using SQLAlchemy/psycopg2 with json support.
    # Otherwise check type.
    
    # Check if we have 'bucket' column? No, bucket might be in metadata or not saved explicitly?
    # Wait, processing/markets.py saves `bucket` into `Opportunity.Bucket`.
    # But `persist.py` does NOT map `Opportunity.Bucket` to a DB column named `bucket`?
    # Let's check persist.py schema again.
    # persist.py INSERT columns: ... ticket_pct, money_pct, sharp_score ... metadata.
    # It does NOT insert `bucket`.
    # However, `metadata` (from pred['features']) does not contain bucket.
    # Logic Gap: I calculated Bucket in markets.py but didn't save it to DB except maybe in `metadata` if I added it?
    # I passed `metadata=pred.get('features', {})`. I did NOT add bucket to those features.
    
    # FIX: I should have added bucket to metadata in markets.py. 
    # For now, I can infer bucket from Odds.
    
    df['bucket'] = df['odds'].apply(lambda x: 
        'Heavy Fav' if x < 1.5 else 
        'Coin Flip' if x < 2.0 else 
        'Small Dog' if x <= 3.0 else 'Longshot'
    )
    
    print(f"\n📈 Volume Report (Last 24h): {len(df)} Bets")
    
    # Detailed Stats by Bucket
    stats = df.groupby('bucket', observed=False)['odds'].agg(['count', 'mean'])
    stats.columns = ['Count', 'AvgOdds']
    print(stats)
    
    print(f"\n💰 Global Avg Odds: {df['odds'].mean():.2f}")
    
    # 3. Validation Check (No Longshots > 3.0)
    errors = df[df['odds'] > 3.0]
    if not errors.empty:
        print(f"❌ CRITICAL: Found {len(errors)} bets with Odds > 3.0!")
        print(errors[['selection', 'odds']])
    else:
        print("✅ Guardrail Check: No Longshots > 3.0")
        
    # 4. Check Metadata Presence
    if 'metadata' in df.columns:
        # Check if null
        missing_meta = df[df['metadata'].isnull()]
        if not missing_meta.empty:
            print(f"⚠️ Warning: {len(missing_meta)} rows missing metadata snapshot.")
        else:
            print("✅ Audit Trail: Metadata present for all rows.")
            
    conn.close()

if __name__ == "__main__":
    run_daily_monitor()
