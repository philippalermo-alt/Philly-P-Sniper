
import os
import sys
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Replicate Fetch Pipeline Logic
from config.settings import Config

# Mock Context
class MockContext:
    def __init__(self):
        self.target_sports = ['NHL']
        self.odds_data = {}
        self.errors = []
    
    def log_error(self, e_type, msg):
        print(f"❌ ERROR [{e_type}]: {msg}")
        self.errors.append(msg)

def execute_verification():
    print("🧪 Starting Verification of Live Odds Filtering (Fetch Stage)...")
    
    # 1. Setup Time
    now_utc = datetime.now(timezone.utc)
    limit_time = now_utc + timedelta(hours=36)
    
    # OLD URL (Simulated Bug)
    # url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets=h2h,spreads,totals&oddsFormat=decimal&commenceTimeTo={iso_limit}"
    
    # NEW URL (Fix)
    iso_start = now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    iso_limit = limit_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    
    url = f"https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets=h2h,totals&oddsFormat=decimal&commenceTimeFrom={iso_start}&commenceTimeTo={iso_limit}"
    
    print(f"🔗 Request URL: {url}")
    print(f"🕒 Current UTC: {now_utc.isoformat()}")
    print(f"🛑 Commence From: {iso_start}")
    
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        
        if isinstance(data, list):
            print(f"📊 Received {len(data)} games.")
            
            failed = False
            for g in data:
                commence = g['commence_time']
                dt_c = datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                
                home = g['home_team']
                away = g['away_team']
                
                time_diff = (dt_c - now_utc).total_seconds()
                
                if time_diff < 0:
                     print(f"❌ FAIL: Found Past/Live Game! {away} @ {home} (Diff: {time_diff}s)")
                     failed = True
                else:
                     print(f"✅ PASS: Future Game: {away} @ {home} (In {time_diff/60:.1f} mins)")
            
            if not failed:
                print("\n✅ VERIFICATION PASSED: No live games returned.")
            else:
                print("\n❌ VERIFICATION FAILED: Live games leaked.")
                
        else:
            print(f"⚠️ API Info: {data}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    execute_verification()
