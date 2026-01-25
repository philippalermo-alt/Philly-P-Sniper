
import pandas as pd
import requests
import time
from datetime import datetime

class SoccerXGClient:
    """
    Client for fetching generic xG stats from FBRef.
    Branding: Philly Edge
    """
    
    # Mapping our internal keys to FBRef URLs
    LEAGUE_URLS = {
        'soccer_epl': 'https://fbref.com/en/comps/9/Premier-League-Stats',
        'soccer_la_liga': 'https://fbref.com/en/comps/12/La-Liga-Stats',
        'soccer_bundesliga': 'https://fbref.com/en/comps/20/Bundesliga-Stats',
        'soccer_serie_a': 'https://fbref.com/en/comps/11/Serie-A-Stats',
        'soccer_ligue_1': 'https://fbref.com/en/comps/13/Ligue-1-Stats',
        'soccer_uefa_champs_league': 'https://fbref.com/en/comps/8/Champions-League-Stats'
    }

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def fetch_xg_table(self, sport_key):
        """
        Fetch the main 'Squad Standard Stats' table which contains xG.
        Returns a DataFrame with Team, xG, xGA, xGDiff.
        """
        url = self.LEAGUE_URLS.get(sport_key)
        if not url:
            print(f"⚠️ League key {sport_key} not supported by FBRef client.")
            return None

        print(f"🌍 Fetching xG data from {url}...")
        
        try:
            # Random sleep to avoid aggressive rate limiting
            time.sleep(1)
            
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                print(f"❌ Failed to fetch FBRef: {resp.status_code}")
                return None
                
            # Parse Tables
            # FBRef usually puts the "Regular Season" table first or second.
            # Look for table with 'xG' in columns.
            dfs = pd.read_html(resp.text)
            
            target_df = None
            for df in dfs:
                # Flask/Pandas html parsing flattens multi-index columns sometimes or keeps them
                # Check for 'xG' or 'Expected'
                if isinstance(df.columns, pd.MultiIndex):
                    # Flatten for check
                    cols = [c[1] if isinstance(c, tuple) else c for c in df.columns]
                else:
                    cols = df.columns
                
                # We look for 'xG' and 'Squad'
                if 'xG' in cols and 'Squad' in cols:
                    target_df = df
                    break
            
            if target_df is None:
                print("❌ Could not find xG table in FBRef response.")
                return None
                
            # Clean Up
            # If MultiIndex, flatten columns
            if isinstance(target_df.columns, pd.MultiIndex):
                target_df.columns = ['_'.join(col).strip() for col in target_df.columns.values]
                
            # Identify columns. Usually 'Unnamed: 0_level_0_Squad' -> 'Team'
            # We want: Squad, Expected_xG, Expected_xGA
            
            # Helper to find column containing substring
            def get_col(substring):
                for c in target_df.columns:
                    if substring in c and '90' not in c: # Avoid per 90 stats for now? Or keep them?
                        return c
                return None

            squad_col = get_col('Squad')
            xg_col = get_col('Expected_xG')
            xga_col = get_col('Expected_xGA')
            
            if not xg_col: 
                # Try simple 'xG' if flattening was different
                xg_col = get_col('xG')
                
            if squad_col and xg_col:
                clean_df = target_df[[squad_col, xg_col]].copy()
                clean_df.columns = ['Team', 'xG']
                
                if xga_col:
                    clean_df['xGA'] = target_df[xga_col]
                else:
                    clean_df['xGA'] = 0.0
                    
                # Return standardized DF
                return clean_df
            
            print("⚠️ Found table but columns didn't match expectation.")
            print("Columns:", target_df.columns)
            return None

        except Exception as e:
            print(f"❌ Error scraping FBRef: {e}")
            return None

if __name__ == "__main__":
    client = SoccerXGClient()
    df = client.fetch_xg_table('soccer_epl')
    if df is not None:
        print("\n✅ PREMIER LEAGUE xG DATA:")
        print(df.sort_values(by='xG', ascending=False).head(10))
    else:
        print("❌ Test Failed.")
