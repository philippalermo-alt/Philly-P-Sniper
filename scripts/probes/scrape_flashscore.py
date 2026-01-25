import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_lineups(url):
    print(f"🚀 Launching Scraper for: {url}")
    
    # Setup Headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(url)
        print("✅ Page Loaded. Waiting for lineups...")
        
        # Wait for lineup container
        wait = WebDriverWait(driver, 10)
        # Wait for the home lineup container class often seen in Flashscore
        # Based on browser research: .wcl-lineops matches generic lineup wrapper or similar
        # simpler: wait for any player name wrapper
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "wcl-nameWrapper_CgKPn")))
        
        # Get Source
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract Home/Away Containers
        # Classes from research: wcl-home_F4S8N (Home), wcl-away_p7P9m (Away)
        # Note: Class names like "_F4S8N" often look hashed/dynamic. 
        # Using partial match if possible or specific classes found.
        
        home_section = soup.find('div', class_=lambda x: x and 'wcl-home_' in x)
        away_section = soup.find('div', class_=lambda x: x and 'wcl-away_' in x)
        
        def extract_players(section):
            if not section: return []
            players = []
            # Find all name wrappers
            wrappers = section.find_all('a', class_=lambda x: x and 'wcl-nameWrapper_' in x)
            for w in wrappers:
                # Find the name span inside
                name_span = w.find('span') # Usually inside the wrapper
                if name_span:
                    players.append(name_span.get_text(strip=True))
                else:
                    players.append(w.get_text(strip=True))
            return players

        home_players = extract_players(home_section)
        away_players = extract_players(away_section)
        
        print(f"\n🏠 HOME LINEUP ({len(home_players)} players):")
        for p in home_players[:11]:
            print(f"  - {p}")
            
        print(f"\n✈️ AWAY LINEUP ({len(away_players)} players):")
        for p in away_players[:11]:
            print(f"  - {p}")

        return home_players, away_players

    except Exception as e:
        print(f"❌ Error: {e}")
        return [], []
    finally:
        driver.quit()

if __name__ == "__main__":
    # URL found by browser agent
    target_url = "https://www.flashscore.com/match/guadalupe-UNs8Witt/herediano-C2Qe7k37/summary/lineups/?mid=Ygn2qPzg"
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    
    scrape_lineups(target_url)
