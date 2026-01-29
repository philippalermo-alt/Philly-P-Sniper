
import os
import sys
import pandas as pd
from datetime import datetime
import pytz

# Add current dir to path to find db
sys.path.append('/app')

from db.connection import get_db
from db.queries import fetch_pending_opportunities

print("🔍 Debugging Dashboard Logic...")

try:
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        sys.exit(1)
        
    print("✅ DB Connected")
    
    # 1. Fetch Data
    df = fetch_pending_opportunities(conn, limit=1000)
    print(f"📦 Fetched {len(df)} pending rows")
    
    if df.empty:
        print("⚠️ DataFrame is empty!")
        sys.exit(0)
        
    # 2. Check for Specific Bets (Game Totals)
    # Look for 'Under 6.5' or team names
    target_bet = df[df['event_id'].astype(str).str.contains('totals_under')]
    print(f"🔎 Found {len(target_bet)} 'totals_under' bets")
    
    if not target_bet.empty:
        row = target_bet.iloc[0]
        print("\n--- Sample Bet ---")
        print(f"ID: {row['event_id']}")
        print(f"Teams: {row['teams']}")
        print(f"Kickoff (Raw): {row['kickoff']} (Type: {type(row['kickoff'])})")
        print(f"Edge: {row['edge']}")
        print(f"User Bet: {row['user_bet']}")
        
        # 3. Apply Dashboard Filters (Replicated)
        
        # A. Clean DF Logic
        # df['kickoff'] = pd.to_datetime(df['kickoff']).dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert('US/Eastern')
        # Replicating step-by-step
        try:
            k_dt = pd.to_datetime(row['kickoff'])
            print(f"Pandas Parsed: {k_dt}")
            
            # Localize
            # Note: If it's naive, localize to UTC. If aware, convert.
            if k_dt.tzinfo is None:
                k_utc = k_dt.tz_localize('UTC')
                print(f" localized to UTC: {k_utc}")
            else:
                k_utc = k_dt
                print(f" already tz-aware: {k_utc}")
                
            k_est = k_utc.tz_convert('US/Eastern')
            print(f" Converted to EST: {k_est}")
            
            # Compare with Now
            now_est = pd.Timestamp.now(tz='US/Eastern')
            print(f" Current EST: {now_est}")
            
            check_future = k_est > now_est
            check_36h = k_est <= (now_est + pd.Timedelta(hours=36))
            
            print(f"FILTER: Future (> Now)? {check_future}")
            print(f"FILTER: Within 36h? {check_36h}")
            
        except Exception as e:
            print(f"❌ Timestamp Error: {e}")
            
        # B. Edge Logic
        edge_val = float(row['edge']) if pd.notnull(row['edge']) else 0.0
        print(f"FILTER: Edge (0.03-0.15)? {0.03 <= edge_val <= 0.15}")
        
        # C. ID Exclusion Logic
        eid = str(row['event_id'])
        is_prop = eid.startswith(('PROP_', 'NHL_'))
        print(f"ID Starts with PROP_/NHL_? {is_prop}")
        print(f"FILTER: Exclusion (~startswith)? {not is_prop}")
        
        # Conclusion
        passes_top15 = check_future and check_36h and (0.03 <= edge_val <= 0.15) and (not is_prop)
        print(f"\n✅ PASSES TOP 15 LOGIC? {passes_top15}")
        
    else:
        print("❌ No 'totals_under' bets found in fetch result.")
        
except Exception as e:
    print(f"❌ CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()
