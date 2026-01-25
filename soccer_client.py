import requests
from config import Config
from key_soccer_players import KEY_SOCCER_PLAYERS
import difflib

class SoccerClient:
    """
    Client for fetching lineups from API-Football and calculating impact.
    """
    BASE_URL = "https://v3.football.api-sports.io"
    
    def __init__(self):
        self.headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': Config.FOOTBALL_API_KEY
        }

    def get_lineups(self, fixture_id):
        """
        Fetch startXI for a fixture.
        Returns (home_players_list, away_players_list) or (None, None)
        """
        if not fixture_id: return None, None
        
        url = f"{self.BASE_URL}/fixtures/lineups"
        params = {'fixture': fixture_id}
        
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=5)
            data = resp.json()
            
            if not data.get('response'):
                return None, None
                
            # Response is a list of 2 teams
            team1 = data['response'][0]
            team2 = data['response'][1]
            
            # Determine which is home (usually first, but check grid)
            # Actually API usually orders by Home/Away in response, but let's just return raw lists
            # The caller (hard_rock_model) matches them to the odds teams.
            
            # Extract names
            def extract_names(team_data):
                names = []
                for p in team_data.get('startXI', []):
                    names.append(p['player']['name'])
                return names

            # We return dicts with team name to help matching
            t1_name = team1['team']['name']
            t2_name = team2['team']['name']
            
            return {t1_name: extract_names(team1)}, {t2_name: extract_names(team2)}

        except Exception as e:
            print(f"⚠️ [SoccerClient] Error fetching lineups: {e}")
            return None, None

    def get_fixture_id(self, home_team, start_date_str):
        """
        Search for fixture ID by Home Team and Date.
        start_date_str: YYYY-MM-DD
        """
        url = f"{self.BASE_URL}/fixtures"
        # We search by team name if we can map it, but fuzzy search is hard via API params.
        # Better: Search by 'date' and filter python-side.
        # But date search returns ALL games (hundreds).
        # Better: Search by team name parameter if we have a robust mapping.
        # Using 'search' param? No, /fixtures allows 'team' and 'date'.
        
        # Challenge: We don't know the API-Football Team ID for "Man City".
        # We only have "Manchester City" text.
        # We should use our `sharp_mapping` or just search by text if API supports it.
        # API-Football doesn't support text search for /fixtures directly without Team ID.
        # But /teams endpoint does.
        
        # Strategy: Search Team Name ONCE to get ID, then search Fixtures.
        # For efficiency in Sentinel, we might just fetch ALL fixtures for the date (one call)
        # and match names locally. This is safer/cheaper than 1 call per game.
        
        params = {'date': start_date_str}
        try:
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = resp.json()
            
            if not data.get('response'):
                return None
                
            # Fuzzy match home team
            best_match = None
            highest_ratio = 0.0
            
            for fixture in data['response']:
                api_home = fixture['teams']['home']['name']
                ratio = difflib.SequenceMatcher(None, home_team, api_home).ratio()
                
                # Check League restriction if needed (e.g. only EPL/La Liga?)
                # For now, just match name
                if ratio > 0.6 and ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = fixture['fixture']['id']
                    
            if highest_ratio > 0.7:
                return best_match
            
            return None

        except Exception as e:
            print(f"⚠️ [SoccerClient] Error searching fixture: {e}")
            return None


    def calculate_impact(self, team_name, starting_xi):
        """
        Calculate xG Penalty for missing stars.
        
        Logic:
        1. Identify stars that belong to this team (Fuzzy Match team name?)
        2. Wait, KEY_SOCCER_PLAYERS doesn't have team mapping.
        3. Simple Heuristic: 
           Check if ANY Star Player from our global list is in the starting XI?
           No, that triggers if Haaland is not playing for Arsenal (which he never does).
           
        Refined Logic:
        We need a mapping of Star -> Team.
        I will assume the lineup passed in IS the team's lineup.
        I need to know WHO SHOULD BE THERE.
        
        Alternative V1 Logic (Simpler):
        Just check who IS playing and Sum their Value.
        Compare Home Star Power vs Away Star Power.
        
        Net Impact = (Home Star Sum) - (Away Star Sum).
        
        If Man City plays (Haaland 0.85 + KDB 0.65 = 1.50)
        vs Arsenal (Saka 0.60 + Odegaard 0.45 = 1.05)
        Net Impact = +0.45 xG favoring City.
        
        This captures "Missing Stars" implicitly. 
        If Haaland is out, City Sum drops to 0.65.
        Net Impact drops to -0.40 (Arsenal favored).
        
        This is MUCH better than "Missing Player" logic because it handles transfers/injuries automatically.
        """
        
        total_impact = 0.0
        kw_found = []
        
        if not starting_xi: return 0.0, []
        
        for player_name in starting_xi:
            # Fuzzy match against KEY_SOCCER_PLAYERS keys
            # "Erling Haaland" vs "Haaland E."
            match = difflib.get_close_matches(player_name, KEY_SOCCER_PLAYERS.keys(), n=1, cutoff=0.6)
            if match:
                key = match[0]
                val = KEY_SOCCER_PLAYERS[key]
                total_impact += val
                kw_found.append(f"{key} ({val})")
                
        return total_impact, kw_found

    def get_team_rolling_xg(self, team_id, last_n=3):
        """
        Fetch last N completed predictions/stats to calculate Rolling Average xG and xGA.
        This provides a quantitative "Form" metric beyond just Wins/Losses.
        
        Args:
            team_id (int): API-Football Team ID.
            last_n (int): Number of games to check. Default 3 to save API calls.
            
        Returns:
            dict: {'avg_xg': float, 'avg_xga': float, 'games_count': int}
        """
        if not team_id:
            return {'avg_xg': 0.0, 'avg_xga': 0.0, 'games_count': 0}
            
        url_fixtures = f"{self.BASE_URL}/fixtures"
        # Get last N completed games
        params = {
            'team': team_id,
            'last': last_n,
            'status': 'FT' # Full Time only
        }
        
        total_xg = 0.0
        total_xga = 0.0
        games_found = 0
        
        try:
            resp = requests.get(url_fixtures, headers=self.headers, params=params, timeout=8)
            data = resp.json()
            
            fixtures = data.get('response', [])
            
            for f in fixtures:
                fix_id = f['fixture']['id']
                
                # We need stats for THIS fixture.
                # Nested call - expensive but necessary if 'teams/statistics' doesn't have it.
                # Try-catch to not break loop
                try:
                    stats_url = f"{self.BASE_URL}/fixtures/statistics?fixture={fix_id}"
                    s_resp = requests.get(stats_url, headers=self.headers, timeout=5)
                    s_data = s_resp.json()
                    
                    if not s_data.get('response'):
                        continue
                        
                    # Find Our Team and Opponent
                    our_stats = None
                    opp_stats = None
                    
                    for tidx in s_data['response']:
                        if tidx['team']['id'] == team_id:
                            our_stats = tidx['statistics']
                        else:
                            opp_stats = tidx['statistics']
                            
                    if our_stats:
                        # Extract xG
                        xg = next((s['value'] for s in our_stats if s['type'] == 'expected_goals'), None)
                        if xg is not None:
                             total_xg += float(xg)
                    
                    if opp_stats:
                        # Opponent xG = Our xGA
                        xga = next((s['value'] for s in opp_stats if s['type'] == 'expected_goals'), None)
                        if xga is not None:
                             total_xga += float(xga)
                             
                    # Only count if we found data (at least xG or xGA)
                    if our_stats or opp_stats:
                        games_found += 1
                        
                except Exception:
                    continue
            
            if games_found > 0:
                return {
                    'avg_xg': round(total_xg / games_found, 2),
                    'avg_xga': round(total_xga / games_found, 2),
                    'games_count': games_found
                }
                
        except Exception as e:
            print(f"⚠️ [SoccerClient] Error fetching rolling xG: {e}")
            
        return {'avg_xg': 0.0, 'avg_xga': 0.0, 'games_count': 0}


if __name__ == "__main__":
    client = SoccerClient()
    # Mock Test
    print("Running Soccer Client Test...")
