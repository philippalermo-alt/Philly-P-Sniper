
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import random
import os

# Basketball-Reference is strict. We need:
# 1. Slow requests (3s+ delay)
# 2. Cloudscraper to bypass CF/403
# 3. Robust error handling

def get_season_refs(start_date="2025-10-22"):
    base_url = "https://www.basketball-reference.com"
    output_file = "nba_ref_assignments_2025_26.csv"
    
    # Init Scraper
    scraper = cloudscraper.create_scraper()
    
    # Check if we can resume
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        if 'Date' in existing_df.columns:
            processed_dates = set(existing_df['Date'].unique())
            print(f"🔄 Resuming... Found {len(existing_df)} games already scraped.")
        else:
            processed_dates = set()
    else:
        existing_df = pd.DataFrame(columns=['Date', 'Home', 'Away', 'Ref1', 'Ref2', 'Ref3', 'Link'])
        processed_dates = set()
        existing_df.to_csv(output_file, index=False)

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.now() - timedelta(days=1) # Yesterday
    
    current_dt = start_dt
    
    while current_dt <= end_dt:
        date_str = current_dt.strftime("%Y-%m-%d")
        
        if date_str in processed_dates:
            print(f"⏩ {date_str} already done. Skipping.")
            current_dt += timedelta(days=1)
            continue
            
        print(f"\n📅 Scraping {date_str}...")
        
        # 1. Get Daily Schedule
        url = f"{base_url}/boxscores/?month={current_dt.month}&day={current_dt.day}&year={current_dt.year}"
        
        try:
            r = scraper.get(url)
            
            if r.status_code == 429:
                print("🛑 RATE LIMIT (429). Sleeping 60s...")
                time.sleep(60)
                continue
                
            soup = BeautifulSoup(r.content, 'html.parser')
            
            # Find all "Box Score" links
            links = []
            # B-Ref structure: div class="game_summary" -> class="gamelink" -> a href
            summaries = soup.find_all('div', class_='game_summary')
            
            day_games = []
            
            for summary in summaries:
                try:
                    # Teams
                    teams = summary.find_all('tr')
                    # usually winner is strong? just get text
                    visit_name = teams[0].find('a').text
                    home_name = teams[1].find('a').text
                    
                    # Link
                    # Use string instead of text to avoid warning
                    link_tag = summary.find('p', class_='links').find('a', string='Box Score')
                    href = link_tag['href']
                    
                    links.append((home_name, visit_name, href))
                except:
                    continue
                    
            print(f"   Found {len(links)} games.")
            
            # 2. Scrape Each Game
            for home, away, href in links:
                 # Delay to avoid ban
                time.sleep(random.uniform(4.0, 7.0)) # Increased delay for safety
                
                box_url = base_url + href
                print(f"   🏀 {away} @ {home}...", end="", flush=True)
                
                try:
                    rb = scraper.get(box_url)
                    if rb.status_code != 200:
                        print(f"❌ Failed {rb.status_code}")
                        continue
                        
                    bsoup = BeautifulSoup(rb.content, 'html.parser')
                    
                    # --- ROBUST EXTRACTION ---
                    refs = []
                    
                    # Method 1: Look for "Officials" text node
                    officials_tag = bsoup.find(string=lambda t: t and "Officials" in t)
                    if officials_tag:
                        parent = officials_tag.parent
                        # usually a <strong> or <div>. Get the parent's parent if needed to find links
                        container = parent.parent if parent.name == 'strong' else parent
                        # Search for links to refs inside this container
                        ref_links = container.find_all('a', href=lambda h: h and '/referees/' in h)
                        refs = [a.text for a in ref_links]

                    # Method 2: Look for scorebox_meta and referee links
                    if not refs:
                        meta = bsoup.find('div', class_='scorebox_meta')
                        if meta:
                            ref_links = meta.find_all('a', href=lambda h: h and '/referees/' in h)
                            refs = [a.text for a in ref_links]
                            
                    if not refs:
                        # Method 3: Broad search in the scorebox content
                        scorebox = bsoup.find('div', class_='scorebox')
                        if scorebox:
                            ref_links = scorebox.find_all('a', href=lambda h: h and '/referees/' in h)
                            refs = [a.text for a in ref_links]
                            
                    if not refs:
                        # Method 4: Search ANYWHERE in body for ref links (fallback)
                        # Filter out common menu links if possible, but B-Ref usually keeps game refs in main content
                        # Let's trust unique names if needed, but for now stick to previous methods.
                        print(f"❌ Refs not found!")
                    else:
                        # Success
                        while len(refs) < 3: refs.append(None)
                        
                        row = {
                            'Date': date_str,
                            'Home': home,
                            'Away': away,
                            'Ref1': refs[0],
                            'Ref2': refs[1],
                            'Ref3': refs[2],
                            'Link': href
                        }
                        day_games.append(row)
                        print(f"✅ {refs[:3]}")

                except Exception as e:
                    print(f"❌ Err: {e}")

            # Save Daily Progress
            if day_games:
                df_new = pd.DataFrame(day_games)
                # Append without header
                df_new.to_csv(output_file, mode='a', header=False, index=False)
                print(f"   💾 Saved {len(day_games)} games.")
            
        except Exception as e:
             print(f"❌ Daily Page Err: {e}")

        current_dt += timedelta(days=1)
        # Larger gap between days
        time.sleep(3)

if __name__ == "__main__":
    get_season_refs()
