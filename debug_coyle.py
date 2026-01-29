
import os
import sys
import pandas as pd
from datetime import datetime
import pytz

sys.path.append('/app')
from db.connection import get_db
from db.queries import fetch_pending_opportunities

print("🔍 Debugging Dashboard Logic (Target: Charlie Coyle)...")

try:
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        sys.exit(1)
        
    # 1. Fetch Data
    df = fetch_pending_opportunities(conn, limit=1000)
    
    # 2. Check for Charlie Coyle
    target = df[df['event_id'].astype(str).str.contains('Charlie Coyle')]
    
    if target.empty:
        print("❌ 'Charlie Coyle' NOT FOUND in DB Query Result.")
        # Print filters used in SQL
        print("SQL used: PENDING + (Time > -48h OR UserBet)")
        sys.exit(0)
        
    print(f"✅ Found {len(target)} rows for Charlie Coyle.")
    row = target.iloc[0]
    
    print("\n--- Prop Details ---")
    print(f"ID: {row['event_id']}")
    print(f"Kickoff (Raw DB): {row['kickoff']} (Type: {type(row['kickoff'])})")
    
    # 3. Simulate Dashboard Time Logic
    try:
        k_dt = pd.to_datetime(row['kickoff'])
        
        # Dashboard Logic:
        # df['kickoff'] = pd.to_datetime(df['kickoff']).dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert('US/Eastern')
        
        if k_dt.tzinfo is None:
            k_utc = k_dt.tz_localize('UTC')
            print(f"Localized Naive to UTC: {k_utc}")
        else:
            k_utc = k_dt
            print(f"Already Aware: {k_utc}")
            
        k_est = k_utc.tz_convert('US/Eastern')
        print(f"Converted to EST: {k_est}")
        
        now_est = pd.Timestamp.now(tz='US/Eastern')
        print(f"Current EST: {now_est}")
        
        # Test Filter: kickoff > now_est
        is_future = k_est > now_est
        print(f"FILTER: is_future (Kickoff > Now)? {is_future}")
        
        if not is_future:
            print("❌ FAILURE: Prop is considered PAST/STARTED. Hidden by Dashboard.")
            diff = now_est - k_est
            print(f"   started {diff} ago.")
        else:
            print("✅ TIME CHECK PASSED.")
            
        # 4. Check Tab 3 Filter
        # (startswith PROP/NHL)
        eid = str(row['event_id'])
        is_prop_tab = eid.startswith(('PROP_', 'NHL_'))
        print(f"FILTER: Starts with PROP/NHL? {is_prop_tab}")
        
    except Exception as e:
        print(f"❌ Time Logic Error: {e}")

except Exception as e:
    print(f"❌ Error: {e}")
