
import requests
import time
import datetime
import random
from bs4 import BeautifulSoup
import pandas as pd

def backfill_nhl_refs():
    # Backfill form start of 2025-26 season 
    start_date = datetime.date(2025, 10, 7)
    end_date = datetime.date.today() - datetime.timedelta(days=1)
    
    print(f"⏳ Backfilling NHL Refs from {start_date} to {end_date}...", flush=True)
    
    # Simple User-Agent Rotation
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    
    assignments = []
    
    current_date = start_date
    consecutive_errors = 0
    
    while current_date <= end_date:
        url = f"https://www.hockey-reference.com/boxscores/index.fcgi?month={current_date.month}&day={current_date.day}&year={current_date.year}"
        print(f"📅 Checking {current_date}: {url}", flush=True)
        
        headers = {'User-Agent': random.choice(user_agents)}
        
        try:
            # Slow down base rate
            time.sleep(random.uniform(5.0, 10.0))
            
            res = requests.get(url, headers=headers)
            
            if res.status_code == 429:
                wait_time = 60 * (2 ** consecutive_errors)
                print(f"⚠️ Rate limit (429)! Sleeping {wait_time}s...", flush=True)
                time.sleep(wait_time)
                consecutive_errors += 1
                if consecutive_errors > 4:
                    print("❌ Too many rate limits. Stopping.", flush=True)
                    break
                continue
                
            if res.status_code != 200:
                print(f"❌ Status {res.status_code} skipping...", flush=True)
                current_date += datetime.timedelta(days=1)
                continue
            
            # Reset error count on success
            consecutive_errors = 0
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            all_links = soup.find_all('a')
            box_links = []
            for l in all_links:
                href = l.get('href', '')
                if '/boxscores/2' in href and 'html' in href and 'index' not in href:
                     box_links.append(href)
            
            box_links = list(set(box_links))
            print(f"   Found {len(box_links)} boxscore links.", flush=True)
            
            for box_link in box_links:
                    full_box_url = f"https://www.hockey-reference.com{box_link}"
                    time.sleep(random.uniform(3.0, 6.0)) 
                    
                    try:
                        box_res = requests.get(full_box_url, headers={'User-Agent': random.choice(user_agents)})
                        if box_res.status_code == 429:
                            print("   ⚠️ Rate limit on box! Skipping...", flush=True)
                            time.sleep(60)
                            continue
                            
                        box_soup = BeautifulSoup(box_res.text, 'html.parser')
                        
                        scorebox = box_soup.find('div', class_='scorebox_meta')
                        officials_text = ""
                        if scorebox:
                            divs = scorebox.find_all('div')
                            for d in divs:
                                if "Officials" in d.get_text():
                                    officials_text = d.get_text().replace("Officials:", "").strip()
                                    break
                                    
                        if officials_text:
                            # Parse Title for Game
                            title = box_soup.title.text if box_soup.title else "Unknown"
                            # Clean "Team A vs Team B Box Score..."
                            title = title.split('Box Score')[0].strip()
                            
                            assignments.append({
                                'Date': current_date,
                                'GameTitle': title,
                                'Officials': officials_text
                            })
                            print(f"   ✅ Found: {title} -> {officials_text[:30]}...", flush=True)
                            
                    except Exception as e:
                        print(f"   ❌ Error fetching box {box_link}: {e}", flush=True)

        except Exception as e:
            print(f"❌ Error fetching schedule: {e}", flush=True)
            
        current_date += datetime.timedelta(days=1)
        
    # Save
    df = pd.DataFrame(assignments)
    df.to_csv("nhl_backfill_refs.csv", index=False)
    print(f"💾 Saved {len(df)} games to nhl_backfill_refs.csv", flush=True)

if __name__ == "__main__":
    backfill_nhl_refs()
