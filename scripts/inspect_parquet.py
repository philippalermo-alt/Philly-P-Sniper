
import pandas as pd

FILE = "data/nhl_processed/nhl_boxscores_3seasons.parquet"

try:
    df = pd.read_parquet(FILE)
    print(f"Columns: {list(df.columns)}")
    print(df.head(1))
    if 'timeOnIcePerGame' in df.columns:
        print("✅ TOI Found!")
    else:
        print("❌ TOI Missing.")
except Exception as e:
    print(f"Error: {e}")
