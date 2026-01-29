import requests
import urllib3
import pandas as pd
import time
import random
import os
import argparse

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def scrape_season(season_end_year):
    """
    Scrape basketball-reference for a given season.
    season_end_year: 2024 for 2023-24 season.
    """
    months = ['october', 'november', 'december', 'january', 'february', 'march', 'april']
    all_games = []
    
    print(f"🏀 Scraping Basketball Reference for {season_end_year}...")
    
    for month in months:
        url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_games-{month}.html"
        print(f"   Fetching {url}...")
        
        try:
            # Random sleep to be nice
            time.sleep(random.uniform(3.0, 5.0))
            
            # Add Headers (Full Browser Mimicry)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.google.com/', # Pretend we came from Google
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Connection': 'keep-alive'
            }
            
            # Fetch content with verified=False to bypass Mac SSL issues
            response = requests.get(url, headers=headers, verify=False)
            if response.status_code != 200:
                print(f"   ⚠️ HTTP {response.status_code} for {url}")
                if response.status_code == 429:
                    print("      (Rate Limit - Waiting 60s...)")
                    time.sleep(60)
                continue
                
            # Use pandas generic read_html on the text content
            tables = pd.read_html(response.text)
            
            # The schedule is usually the first table
            df = tables[0]
            
            # Clean up headers
            # BBRef handles 'Playoffs' rows mixed in.
            df = df[df['Date'] != 'Playoffs']
            df = df[df['Date'] != 'Date'] # Header rows
            
            all_games.append(df)
            
        except ValueError as e:
            # "No tables found" means the month might not have games (e.g. Oct in some years)
            if "No tables found" not in str(e):
                print(f"   ⚠️ Warning: {e}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
    if not all_games:
        print("❌ No data found.")
        return None
        
    full_df = pd.concat(all_games, ignore_index=True)
    
    # Rename Columns
    # Typically: Date, Start (ET), Visitor/Neutral, PTS, Home/Neutral, PTS.1, Box Score, OT, Attend., Notes
    
    # Normalize
    rename_map = {
        'Visitor/Neutral': 'AwayTeam',
        'PTS': 'AwayScore',
        'Home/Neutral': 'HomeTeam',
        'PTS.1': 'HomeScore',
        'Start (ET)': 'Time',
    }
    full_df.rename(columns=rename_map, inplace=True)
    
    # Add Season Column
    full_df['Season'] = season_end_year
    
    print(f"✅ Scraped {len(full_df)} games.")
    return full_df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--season', type=int, required=True, help="Season End Year (2024 for 2023-24)")
    parser.add_argument('--out', type=str, default="nba_bbref_stats.csv")
    args = parser.parse_args()
    
    df = scrape_season(args.season)
    if df is not None:
        if os.path.exists(args.out):
            df.to_csv(args.out, mode='a', header=False, index=False)
        else:
            df.to_csv(args.out, index=False)
        print(f"💾 Saved to {args.out}")

if __name__ == "__main__":
    main()
