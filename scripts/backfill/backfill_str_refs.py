
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re

def backfill_str_archive():
    print("⏳ Starting Backfill from ScoutingTheRefs Archive (Search)...", flush=True)
    
    # Use Search Pagination (Reliable)
    base_url = "https://scoutingtherefs.com/page/{}/?s=todays+nhl+referees"
    assignments = []
    
    scraper = cloudscraper.create_scraper()
    
    found_posts = 0
    
    for page_num in range(1, 25): 
        print(f"📄 Scanning Page {page_num}...", flush=True)
        url = base_url.format(page_num)
        
        try:
            # Random sleep to avoid rapid fire
            time.sleep(random.uniform(2.0, 5.0))
            
            res = scraper.get(url)
            if res.status_code != 200:
                print(f"   ❌ Page {page_num} failed: {res.status_code}", flush=True)
                # If 403/429, maybe wait longer?
                if res.status_code in [403, 429]:
                    time.sleep(30)
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            articles = soup.find_all('article')
            
            if not articles:
                print("   ❌ No articles found. Stopping.")
                break
                
            for art in articles:
                link = art.find('a')
                if not link: continue
                
                href = link.get('href', '')
                title = link.get_text(strip=True)
                
                # Filter for "Today's NHL Referees"
                if "nhl-referees" in href.lower() or "nhl referees" in title.lower():
                    # This is a target post
                    print(f"   🔗 Found Post: {title}")
                    
                    # Fetch Post Content
                    # Delay
                    time.sleep(random.uniform(1.0, 2.5))
                    
                    try:
                         post_res = scraper.get(href)
                         post_soup = BeautifulSoup(post_res.text, 'html.parser')
                         
                         # --- PARSING LOGIC (From nhl_assignments.py) ---
                         # 2. Parse Tables
                         tables = post_soup.find_all('table')
                         
                         # Get Date from Title or Post Date
                         # Usually URL has date: /2025/10/42312/...
                         # Parse date from URL
                         date_match = re.search(r'/(\d{4})/(\d{2})/', href)
                         game_date = "Unknown"
                         if date_match:
                             game_date = f"{date_match.group(1)}-{date_match.group(2)}"
                             # We ignore exact day for now, or assume it's "Today"
                             # Ideally we parse the "date" listed in the post title?
                             # Title: "Today's NHL Referees ... 10/7/25"
                             
                         # Try to parse specific date from URL Slug (e.g. ...-1-20-26/)
                         # Regex: -(\d{1,2})-(\d{1,2})-(\d{2,4})
                         slug_date = re.search(r'-(\d{1,2})-(\d{1,2})-(\d{2,4})/?$', href)
                         if slug_date:
                             # 2026-01-20 format
                             try:
                                 y = slug_date.group(3)
                                 if len(y) == 2: y = "20" + y
                                 game_date = f"{y}-{slug_date.group(1).zfill(2)}-{slug_date.group(2).zfill(2)}"
                             except:
                                 pass
                                 
                         # Legacy Check (Title)
                         if game_date == "Unknown":
                              d_search = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', title)
                              if d_search:
                                 game_date = d_search.group(1)
                             
                         # Parse Games
                         for table in tables:
                            if "REFEREES" not in table.get_text() and "Linesmen" not in table.get_text():
                                 continue
                                 
                            # Back-search for Game Title
                            game_title = "Unknown Game"
                            prev = table.previous_element
                            steps = 0
                            while prev and steps < 50:
                                if getattr(prev, 'name', None) in ['h1','h2','h3','h4','p','strong']:
                                    txt = prev.get_text(strip=True)
                                    if (" at " in txt or " vs " in txt) and len(txt) < 100:
                                        game_title = txt
                                        break
                                prev = getattr(prev, 'previous_element', None)
                                steps += 1
                                
                            # Extract Refs
                            refs = []
                            rows = table.find_all('tr')
                            for row in rows:
                                txts = [c.get_text(separator=' ', strip=True) for c in row.find_all('td')]
                                full_row_text = " ".join(txts)
                                matches = re.findall(r"([A-Za-z\.\-\' ]+)\s+#\d+", full_row_text)
                                for m in matches:
                                    name = m.strip()
                                    if name and name not in refs and "Referees" not in name:
                                        refs.append(name)
                                        
                            if len(refs) >= 2:
                                assignments.append({
                                    'Date': game_date,
                                    'Game': game_title,
                                    'Officials': refs
                                })
                                found_posts += 1
                                print(f"      ✅ {game_date} | {game_title} -> {refs[:2]}...")
                                
                    except Exception as e:
                        print(f"      ❌ Failed post {href}: {e}")

        except Exception as e:
            print(f"❌ Error Page {page_num}: {e}")
            
        time.sleep(random.uniform(2.0, 4.0))
        
    # Save
    df = pd.DataFrame(assignments)
    df.to_csv("nhl_backfill_str.csv", index=False)
    print(f"\n💾 Saved {len(df)} entries to nhl_backfill_str.csv")

if __name__ == "__main__":
    backfill_str_archive()
