
import os
import pandas as pd
from pybaseball import statcast
from datetime import datetime
import time

# Target: 3 Years of Data
YEARS = [2023, 2024, 2025]
MONTHS = [
    ('03-20', '04-30'), # Start late March
    ('05-01', '05-31'),
    ('06-01', '06-30'),
    ('07-01', '07-31'),
    ('08-01', '08-31'),
    ('09-01', '09-30'),
    ('10-01', '11-05')  # Playoffs
]

OUTPUT_FILE = "mlb_statcast_2023_2025.csv"

def backfill_mlb():
    print("⚾️ Starting MLB Statcast Backfill (2023-2025)...")
    
    first_batch = True
    
    # Check if file exists to determine header need
    if os.path.exists(OUTPUT_FILE):
        first_batch = False
        print(f"ℹ️ Appending to existing file: {OUTPUT_FILE}")

    today = datetime.now().date()
    
    for year in YEARS:
        print(f"\n📅 Processing Season {year}...")
        
        # Create weekly chunks for the season (March 20 to Nov 5)
        season_start = datetime(year, 3, 20).date()
        season_end = datetime(year, 11, 5).date()
        
        current_start = season_start
        while current_start <= season_end:
            # 7-day chunks
            current_end = current_start + pd.Timedelta(days=6)
            
            # Clip to season end and today
            if current_end > season_end:
                current_end = season_end
            if current_start > today:
                break
            
            eff_end = current_end if current_end <= today else today
            
            s_str = current_start.strftime("%Y-%m-%d")
            e_str = eff_end.strftime("%Y-%m-%d")
            
            print(f"   Fetching {s_str} to {e_str}...", end="", flush=True)
            
            try:
                # Small chunk fetch
                df = statcast(start_dt=s_str, end_dt=e_str)
                
                if df is not None and not df.empty:
                    print(f" ✅ {len(df)} pitches. Saving...")
                    # Incremental Write
                    df.to_csv(OUTPUT_FILE, mode='a', header=first_batch, index=False)
                    first_batch = False
                    
                    # Aggressive Cleanup
                    del df
                    import gc
                    gc.collect()
                else:
                    print(f" ⚠️ No data.")
                    
            except Exception as e:
                print(f" ❌ Error: {e}")
                
            # Advance
            current_start = current_end + pd.Timedelta(days=1)
            
            # Polite sleep to keep CPU/Net happy
            time.sleep(5)
            
    print("✅ Backfill Complete!")

if __name__ == "__main__":
    backfill_mlb()
