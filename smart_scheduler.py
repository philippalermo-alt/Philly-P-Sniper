import os
import pytz
from datetime import datetime
from hard_rock_model import run_sniper
from settle_props import settle_props
from closing_line import fetch_closing_odds

def main():
    # Set timezone to US/Eastern
    tz = pytz.timezone('US/Eastern')
    now = datetime.now(tz)
    
    current_hour = now.hour
    weekday = now.weekday() # 0=Mon, 6=Sun
    
    # Schedule Configuration (Hours in 24h format)
    # Mon-Fri (0-4): 7 AM (7), 5 PM (17)
    # Sat-Sun (5-6): 7 AM (7), 12 PM (12), 5 PM (17)
    
    should_run = False
    
    if weekday < 5: # Weekday
        if current_hour in [7, 17]:
            should_run = True
    else: # Weekend
        if current_hour in [7, 12, 17]:
            should_run = True
            
    # Debug override via env var (for testing)
    if os.getenv('FORCE_RUN') == 'true':
        should_run = True
        
    print(f"🕒 Checker running at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"📅 Day: {now.strftime('%A')} | Hour: {current_hour}")
    
    if should_run:
        print("✅ Schedule Match! Execution starting...")
        try:
            print("📉 Fetching Closing Odds (CLV)...")
            fetch_closing_odds()
            
            run_sniper()
            print("🏒 Running Prop Settlement...")
            settle_props()
            print("🚀 Job completed successfully.")
        except Exception as e:
            print(f"❌ Job failed: {e}")
    else:
        print("💤 No schedule match. Skipping execution.")
        print("ℹ️  Schedule: Mon-Fri (7, 17), Sat-Sun (7, 12, 17) EST")

if __name__ == "__main__":
    main()
