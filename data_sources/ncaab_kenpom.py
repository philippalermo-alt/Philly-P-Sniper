from kenpompy.utils import login
from kenpompy.summary import get_efficiency
import pandas as pd
import os
import time

class KenPomClient:
    """
    Client for fetching NCAAB efficiency metrics from KenPom.com.
    """
    def __init__(self):
        # Prefer browser session or login details if available
        # Note: kenpompy usually requires a browser object (mechanicalsoup) logged in
        self.email = os.getenv('KENPOM_EMAIL')
        self.password = os.getenv('KENPOM_PASSWORD')
        self.browser = None
        
        # If using API key (official), we might need a custom requester. 
        # But 'kenpompy' is a scraper.
        # User has KENPOM_API_KEY in config, implying OFFICIAL API use?
        # The user asked "Can we not use any data from KenPom api for NCAA?" earlier...
        # Wait, the prompt said "Can we not use any data from KenPom api" -> meaning "Can we USE it?" 
        # or "Is there a way to avoid it?" -> Context: "I need to find an API... API-Football...".
        # User later said "We are not using Docker...".
        # Then "Can we not use any data from KenPom api for NCAA?"
        # I interpreted as "Why aren't we using data from KenPom?".
        # Let's support both or assume scraper if API key fails.
        pass

    def login(self):
        if not self.email or not self.password:
            print("⚠️ KenPom credentials (EMAIL/PASSWORD) not found. Cannot scrape.")
            return False
        try:
            self.browser = login(self.email, self.password)
            return True
        except Exception as e:
            print(f"❌ KenPom Login failed: {e}")
            return False

    def get_efficiency_stats(self, season=None):
        """
        Fetch summary efficiency stats (AdjEM, AdjO, AdjD).
        """
        if not self.browser:
            if not self.login():
                return pd.DataFrame()
        
        try:
            # Default to current season if None
            df = get_efficiency(self.browser, season=season)
            # Columns usually: Team, Conf, W-L, AdjEM, AdjO, AdjD, ...
            # We care about 'Team' and 'AdjEM'
            return df[['Team', 'AdjEM', 'AdjO', 'AdjD', 'AdjT']]
        except Exception as e:
            print(f"❌ Error fetching KenPom stats (kenpompy): {e}")
            
        # Fallback to Cloudscraper
        print("⚠️ Attempting Cloudscraper fallback...")
        return self._scrape_via_cloudscraper(season)

    def _scrape_via_cloudscraper(self, season=None):
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            
            # Login
            login_url = "https://kenpom.com/handlers/login_handler.php"
            payload = {
                "email": self.email,
                "password": self.password,
                "submit": "Login"
            }
            res = scraper.post(login_url, data=payload)
            
            # Fetch Homepage (Summary Stats)
            url = "https://kenpom.com/index.php"
            if season:
                url += f"?y={season}"
                
            res = scraper.get(url)
            if res.status_code != 200:
                print(f"❌ Cloudscraper Error: {res.status_code}")
                return pd.DataFrame()

            # Parse Table
            # Pandas read_html returns a list of dfs
            dfs = pd.read_html(res.text)
            for df in dfs:
                # Look for the main table
                if 'AdjEM' in df.columns or ('AdjEM', 'AdjEM') in df.columns:
                    # Clean up multi-index headers if present
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(0)
                    
                    # Ensure columns exist
                    cols = ['Team', 'AdjEM', 'AdjO', 'AdjD', 'AdjT']
                    # Some might be slightly different named or indexed
                    # Rename if necessary or strict select
                    # KenPom columns: Rank, Team, Conf, W-L, AdjEM, AdjO, AdjD, AdjT, Luck, ...
                    # Check if 'AdjT' exists (Tempo)
                    if 'AdjT' not in df.columns and 'Tempo' in df.columns:
                        df['AdjT'] = df['Tempo'] # mapping
                        
                    return df[cols]
            
            print("❌ No efficiency table found in Cloudscraper response.")
            return pd.DataFrame()

        except Exception as e:
            print(f"❌ Cloudscraper Fallback Failed: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    client = KenPomClient()
    print("Fetching KenPom Efficiency...")
    df = client.get_efficiency_stats()
    if not df.empty:
        print(df.head())
    else:
        print("Failed (Check credentials).")
