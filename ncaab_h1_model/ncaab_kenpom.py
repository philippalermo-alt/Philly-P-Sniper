from kenpompy.utils import login
from kenpompy.summary import get_efficiency
import pandas as pd
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class KenPomClient:
    """
    Client for fetching NCAAB efficiency metrics from KenPom.com.
    """
    def __init__(self):
        self.api_key = os.getenv('KENPOM_API_KEY')
        self.base_url = "https://kenpom.com/api.php"

    def get_efficiency_stats(self, season=None):
        """
        Fetch summary efficiency stats (AdjEM, AdjO, AdjD, AdjT) via Official API.
        """
        if not self.api_key:
            print("⚠️ KENPOM_API_KEY not found. Cannot fetch data.")
            return pd.DataFrame()

        try:
            import requests
            
            # Default to current year logic if needed, or hardcode/pass from arg
            # season year is the ending year (e.g., 2026)
            year = season if season else 2026
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            params = {
                "endpoint": "ratings",
                "y": year
            }
            
            response = requests.get(self.base_url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"❌ KenPom API Error: {response.status_code} - {response.text}")
                return pd.DataFrame()

            data = response.json()
            
            # API returns a list of dictionaries? Or a dict with keys?
            # Docs say "Response Format: JSON" and lists fields. Likely a list of objects.
            
            if not data:
                print("❌ KenPom API returned empty data.")
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            
            # Column Mappings based on API Docs
            # TeamName -> Team
            # AdjEM -> AdjEM
            # AdjOE -> AdjO
            # AdjDE -> AdjD
            # AdjTempo -> AdjT
            
            rename_map = {
                'TeamName': 'Team',
                'AdjOE': 'AdjO',
                'AdjDE': 'AdjD',
                'AdjTempo': 'AdjT'
            }
            df = df.rename(columns=rename_map)
            
            # Ensure required columns exist
            required = ['Team', 'AdjEM', 'AdjO', 'AdjD', 'AdjT']
            
            # Filter
            existing = [c for c in required if c in df.columns]
            if len(existing) < len(required):
                print(f"⚠️ Missing columns in API data. Found: {existing}")
                return pd.DataFrame()
            
            return df[required]

        except Exception as e:
            print(f"❌ Error fetching KenPom API stats: {e}")
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
