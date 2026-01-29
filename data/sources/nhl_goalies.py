import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import difflib
from utils.logging import log
from utils.team_names import normalize_team_name

# Mapping DFO Team Names to Our Internal Normalized Names
# DFO usually uses full names or common abbreviations.
# We'll use our normalize_team_name utility, but might need manual overrides.

def fetch_dailyfaceoff_goalies():
    """
    Scrapes DailyFaceoff for starting goalies.
    Returns a dict: { 'Normalized Team Name': {'starter': 'Name', 'status': 'Confirmed/Likely'} }
    """
    url = "https://www.dailyfaceoff.com/starting-goalies"
    
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    import shutil

    try:
        log("GOALIE_SCRAPER", f"Fetching {url} (via Selenium)...")
        
        # Selenium Setup
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # Modern headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User Agent (Spoofing)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Driver Resolution
        # In Docker, we might have chromedriver in PATH.
        # Check if shutil.which("chromedriver") exists, else use Manager.
        driver_path = shutil.which("chromedriver")
        if driver_path:
             service = Service(driver_path)
             driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
             # Fallback (Slow but works if internet access allowed for installation)
             driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # Optional: Wait for content?
        import time
        time.sleep(5) 
        
        html_content = driver.page_source
        driver.quit()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # DFO Structure (approximate, robust search)
        # They use <article class="matchup"> or similar.
        # We need to find the specific containers.
        # 2026 Check: DFO layout changes often. 
        # Strategy: Find "Matchup" blocks, then find "Goalie" blocks within.
        
        goalie_data = {}
        
        # Specific DFO selectors (as of late 2025/2026 common patterns)
        # Often: div[class*="MatchupCard"]
        matchups = soup.select('div[class*="MatchupCard"]')
        
        if not matchups:
            # Fallback for older/mobile layout
            matchups = soup.select('article')
            
        log("GOALIE_SCRAPER", f"Found {len(matchups)} matchup blocks.")
        
        for m in matchups:
            try:
                # 1. Extract Teams from Header (e.g. "Washington Capitals at Seattle Kraken")
                # Selector: span.text-3xl
                header_span = m.select_one('span.text-3xl')
                if not header_span:
                    continue
                
                header_text = header_span.get_text(" ", strip=True) 
                
                if " at " in header_text:
                    teams_split = header_text.split(" at ")
                elif " vs " in header_text:
                    teams_split = header_text.split(" vs ")
                else:
                    continue
                    
                away_team_raw = teams_split[0].strip()
                home_team_raw = teams_split[1].strip()
                
                # 2. Extract Goalies (Left Col = Away, Right Col = Home)
                # Use attribute selector to avoid escaping issues with w-1/2
                cols = m.select('div[class*="w-1/2"]')
                if len(cols) < 2:
                    continue
                    
                # Helper to extract from column
                def extract_goalie_info(col, side):
                    # Name regex or strict selector
                    # Found: <span class="text-center text-lg xl:text-2xl">Logan Thompson</span>
                    name_span = col.select_one('span[class*="text-lg"]')
                    name = name_span.get_text(strip=True) if name_span else "Unknown"
                    
                    # Status
                    status = "Projected"
                    for s in col.select('span'):
                        txt = s.get_text(strip=True).lower()
                        if txt in ['confirmed', 'likely', 'unconfirmed', 'expected']:
                            status = txt.capitalize()
                            break
                        
                    return name, status

                away_goalie, away_status = extract_goalie_info(cols[0], "Away")
                home_goalie, home_status = extract_goalie_info(cols[1], "Home")
                
                if away_goalie == "Unknown" or home_goalie == "Unknown":
                    continue

                # Normalize Teams
                norm_away = normalize_team_name(away_team_raw)
                norm_home = normalize_team_name(home_team_raw)
                
                # Store
                goalie_data[norm_away] = {'starter': away_goalie, 'status': away_status, 'source': 'DailyFaceoff'}
                goalie_data[norm_home] = {'starter': home_goalie, 'status': home_status, 'source': 'DailyFaceoff'}
                
            except Exception as e:
                continue
                
        log("GOALIE_SCRAPER", f"✅ Parsed starters for {len(goalie_data)} teams.")
        return goalie_data

    except Exception as e:
        log("GOALIE_SCRAPER", f"❌ Error: {e}")
        return {}

if __name__ == "__main__":
    # Test Run
    data = fetch_dailyfaceoff_goalies()
    for team, info in data.items():
        print(f"{team}: {info['starter']} ({info['status']})")
