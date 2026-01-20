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
            print(f"❌ Error fetching KenPom stats: {e}")
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
