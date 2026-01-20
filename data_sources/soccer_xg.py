import requests
import os
import pandas as pd
from datetime import datetime, timedelta

class SoccerXGClient:
    """
    Client for fetching Soccer Expected Goals (xG) from API-Football.
    """
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('FOOTBALL_API_KEY')
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            'x-apisports-key': self.api_key
        }

    def get_recent_fixtures(self, team_id, last_n=5):
        """
        Get last N fixtures for a team.
        """
        url = f"{self.base_url}/fixtures"
        params = {
            'team': team_id,
            'last': last_n,
            'status': 'FT'  # Finished games only
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get('response', [])
        except Exception as e:
            print(f"Error fetching fixtures for team {team_id}: {e}")
            return []

    def get_fixture_stats(self, fixture_id, team_id=None):
        """
        Get statistics for a specific fixture, extracting xG if available.
        """
        url = f"{self.base_url}/fixtures/statistics"
        params = {'fixture': fixture_id}
        if team_id:
            params['team'] = team_id
            
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            # Response is a list of teams stats. 
            # item = { 'team': {...}, 'statistics': [ { 'type': 'Expected Goals', 'value': 1.2 }, ... ] }
            return data.get('response', [])
        except Exception as e:
            print(f"Error fetching stats for fixture {fixture_id}: {e}")
            return []

    def get_average_xg(self, team_id, last_n=5):
        """
        Calculate average xG for a team over last N games.
        """
        fixtures = self.get_recent_fixtures(team_id, last_n)
        if not fixtures:
            return 0.0

        total_xg = 0.0
        count = 0

        for f in fixtures:
            fid = f['fixture']['id']
            stats = self.get_fixture_stats(fid, team_id)
            if not stats:
                continue
            
            # Extract xG
            # stats structure: [ { "team": ..., "statistics": [...] } ]
            # If we filtered by team_id, should be size 1 list.
            team_stats = stats[0].get('statistics', [])
            xg_stat = next((s for s in team_stats if s['type'] == 'expected_goals'), None)
            
            # API-Football sometimes labels it "Expected Goals" or "expected_goals"? 
            # Usually "Expected Goals" in the value 'type'.
            if not xg_stat:
                xg_stat = next((s for s in team_stats if s['type'] == 'Expected Goals'), None)

            if xg_stat and xg_stat['value'] is not None:
                try:
                    total_xg += float(xg_stat['value'])
                    count += 1
                except ValueError:
                    pass
            
            # Rate limit safety (free tier is 10/min? No, 100/day usually, but let's be safe)
            # time.sleep(0.2) 

        return round(total_xg / count, 2) if count > 0 else 0.0

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Example: Manchester City (ID: 50)
    client = SoccerXGClient()
    print("Fetching Man City xG...")
    avg_xg = client.get_average_xg(50, last_n=3)
    print(f"Average xG (last 3 games): {avg_xg}")
