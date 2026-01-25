
from pybaseball import statcast
import pandas as pd

def test_statcast():
    print("⚾️ Testing Statcast Connection...")
    # Fetch Data for Oct 25, 2024 (World Series Game 1)
    try:
        data = statcast(start_dt='2024-10-25', end_dt='2024-10-25')
        if not data.empty:
            print(f"✅ Success! Fetched {len(data)} pitches.")
            print("   Columns:", list(data.columns)[:5])
            print("   Sample Pitcher:", data.iloc[0]['player_name'])
        else:
            print("⚠️ Data fetched but empty frame returned.")
    except Exception as e:
        print(f"❌ Failed to fetch Statcast data: {e}")

if __name__ == "__main__":
    test_statcast()
