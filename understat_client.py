import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from config import Config

# Configure Logger
logger = logging.getLogger("UnderstatClient")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

class UnderstatClient:
    """
    Selenium-based scraper for Understat.com.
    Extracts deep player metrics (xG, xGChain, xGBuildup) by reading
    JavaScript objects directly from browser memory.
    """
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Initialize Chrome Driver with stealth options."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Suppress logs
        chrome_options.add_argument("--log-level=3")
        
        try:
            # On AWS/Linux (Docker/Ubuntu), use system installed driver if available
            import os
            if os.path.exists("/usr/bin/chromedriver"):
                service = Service("/usr/bin/chromedriver")
            elif os.path.exists("/usr/lib/chromium-browser/chromedriver"):
                 service = Service("/usr/lib/chromium-browser/chromedriver")
            else:
                # Fallback for Local Mac
                service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Failed to init Chrome Driver: {e}")
            raise e

    def get_league_matches(self, league: str, season: str) -> list:
        """
        Get all matches for a given league and season.
        Returns a list of match dictionaries (id, h/a teams, datetime, isResult).
        """
        if not self.driver:
            self._init_driver()
            
        url = f"https://understat.com/league/{league}/{season}"
        try:
            logger.info(f"Fetching matches for {league} {season}...")
            self.driver.get(url)
            time.sleep(2) # Allow for redirect/load
            
            # Extract datesData
            dates_data = self.driver.execute_script("return window.datesData;")
            
            if not dates_data:
                logger.warning(f"No datesData found for {league} {season}")
                return []
                
            matches = []
            for match in dates_data:
                matches.append({
                    "id": match.get("id"),
                    "home_team": match.get("h", {}).get("title"),
                    "away_team": match.get("a", {}).get("title"),
                    "datetime": match.get("datetime"),
                    "is_result": match.get("isResult", False),
                    "goals_h": match.get("goals", {}).get("h"),
                    "goals_a": match.get("goals", {}).get("a"),
                    "xg_h": match.get("xG", {}).get("h"),
                    "xg_a": match.get("xG", {}).get("a"),
                })
                
            logger.info(f"Found {len(matches)} matches for {league} {season} ({len([m for m in matches if m['is_result']])} completed)")
            return matches
            
        except Exception as e:
            logger.error(f"Error fetching league matches: {e}")
            return []

    def get_match_data(self, match_id):
        """
        Fetch full match data including lineups, player xG, and shot data.
        """
        if not self.driver:
            self._init_driver()
            
        url = f"https://understat.com/match/{match_id}"
        logger.info(f"Navigating to {url}...")
        
        try:
            self.driver.get(url)
            time.sleep(1.5) 
            
            # Extract JS Variables directly
            data = self.driver.execute_script("""
                return {
                    match_info: typeof match_info !== 'undefined' ? match_info : null,
                    rosters: typeof rostersData !== 'undefined' ? rostersData : null,
                    shots: typeof shotsData !== 'undefined' ? shotsData : null
                };
            """)
            
            if not data['rosters']:
                logger.warning("rostersData not found in page.")
                return None
                
            # Process/Clean Data
            cleaned_players = []
            
            match_info = data.get('match_info', {})
            team_h = match_info.get('team_h', 'Home')
            team_a = match_info.get('team_a', 'Away')
            
            rosters = data.get('rosters', {})
            for team_id, players in rosters.items():
                real_team_name = team_h if team_id == 'h' else team_a
                
                for pid, stats in players.items():
                    stats['team_id'] = team_id
                    stats['team_name'] = real_team_name 
                    stats['id'] = pid 
                    stats['xG'] = float(stats.get('xG', 0))
                    stats['xA'] = float(stats.get('xA', 0))
                    stats['xGChain'] = float(stats.get('xGChain', 0))
                    stats['xGBuildup'] = float(stats.get('xGBuildup', 0))
                    cleaned_players.append(stats)
            
            logger.info(f"Extracted stats for {len(cleaned_players)} players.")
            
            return {
                'match_id': match_id,
                'match_info': data.get('match_info'),
                'players': cleaned_players
            }
            
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return None

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

if __name__ == "__main__":
    client = UnderstatClient(headless=True)
    matches = client.get_league_matches("EPL", "2023")
    if matches:
        print(f"Success! Found {len(matches)} matches.")
    client.quit()
