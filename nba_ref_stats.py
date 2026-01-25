
import requests
import pandas as pd
from datetime import datetime
import os

def scrape_nba_stuffer_refs():
    url = "https://www.nbastuffer.com/2025-2026-nba-referee-stats/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    print(f"🕵️‍♂️ Fetching Ref Stats from {url}...")
    
    try:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"❌ Failed: {r.status_code}")
            return None
            
        # Parse tables
        dfs = pd.read_html(r.text)
        
        if not dfs:
            print("❌ No tables found.")
            return None
            
        # The main table is likely the first one
        df = dfs[0]
        
        # Clean columns
        # Expected: RANK, REFEREE, ROLE, GENDER, EXPERIENCE (YEARS), GAMES OFFICIATED, HOME TEAM WIN%, POINTS DIFFERENTIAL, TOTAL POINTS, CALLED FOULS, FOUL% RD, FOUL% HM, DIFF
        
        print(f"✅ Found table with {len(df)} rows.")
        print("Columns:", df.columns.tolist())
        
        # Renaissance Ref Names: "Scott Foster" -> "Scott Foster" matches our other scraper
        # Save to CSV
        output_path = "nba_ref_stats_2025_26.csv"
        df.to_csv(output_path, index=False)
        print(f"💾 Saved to {output_path}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    scrape_nba_stuffer_refs()
