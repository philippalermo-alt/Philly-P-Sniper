import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import os

class NHLRefClient:
    def __init__(self):
        self.base_url = "https://api-web.nhle.com/v1"
        self.output_file = "nhl_ref_game_logs.csv"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }

    def fetch_season_logs(self, start_date="2025-10-04", end_date=None):
        """
        Iterates through the schedule week by week to build a ref game log.
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        stop_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_logs = []
        
        print(f"🏒 Fetching NHL Ref Data from {start_date} to {end_date}...")

        while current_date <= stop_date:
            date_str = current_date.strftime("%Y-%m-%d")
            # Fetch Weekly Schedule
            url = f"{self.base_url}/schedule/{date_str}"
            try:
                r = requests.get(url, headers=self.headers)
                if r.status_code == 200:
                    data = r.json()
                    
                    # DEBUG: Dump Schedule
                    if not os.path.exists("debug_schedule.json"):
                        import json
                        with open("debug_schedule.json", "w") as f:
                            json.dump(data, f, indent=2)
                        print("💾 Saved debug_schedule.json")
                        
                    game_weeks = data.get('gameWeek', [])
                    
                    for day in game_weeks:
                        for game in day.get('games', []):
                            # Skip if game not final
                            if game.get('gameState') not in ['FINAL', 'OFF']:
                                continue
                                
                            g_id = game['id']
                            # Process Game
                            log = self.fetch_game_boxscore(g_id)
                            if log:
                                all_logs.append(log)
                            else:
                                print(f"❌ Failed to parse boxscore for {g_id}")
                                
                else:
                    print(f"⚠️ Failed schedule fetch for {date_str}: {r.status_code}")

            except Exception as e:
                print(f"❌ Error fetching schedule: {e}")
            
            # Jump 7 days
            current_date += timedelta(days=7)
            time.sleep(1) # Be polite

        # Convert to DataFrame
        df = pd.DataFrame(all_logs)
        if not df.empty:
            df.to_csv(self.output_file, index=False)
            print(f"✅ Saved {len(df)} game logs to {self.output_file}")
            print(df.head())
        else:
            print("⚠️ No game logs processed.")

    def fetch_game_boxscore(self, game_id):
        url = f"{self.base_url}/game/{game_id}/boxscore"
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code != 200:
                return None
                
            data = r.json()
            
            # 1. Officials
            # Usually in 'gameOutcome' or just 'officials'?
            # Check widely known structure: data['officials'] -> list
            # Actually for V1 API it might be different. Let's look for 'officials'
            # Note: 2024/25 API update moved things.
            # Assuming 'boxscore' -> 'officials' or root 'officials' doesn't exist?
            # Common path: data['gameOutcome'] sometimes?
            # Let's try raw extraction.
            
            officials = []
            # Check various keys as API shifts
            # Try 1: Root 'officials' (Some endpoints)
            # Try 2: 'boxscore' -> 'officials' (Current hypothesis)
            # Actually, recent reports say Boxscore endpoint has no officials.
            # We might need the 'Landing' endpoint: https://api-web.nhle.com/v1/game/{id}/landing
            
            # Let's Try Landing Endpoint if Officials missing here?
            # Wait, let's assume we use Landing endpoint for everything if Boxscore is slim.
            # Switching URL to Landing for safety (it has everything)
            pass 
        except:
            return None

    def fetch_game_landing(self, game_id):
        """
        Uses /landing endpoint which is richer.
        """
        url = f"{self.base_url}/game/{game_id}/landing"
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code != 200: return None
            data = r.json()
            
            home_team = data.get('homeTeam', {}).get('abbrev')
            away_team = data.get('awayTeam', {}).get('abbrev')
            
            # 1. Penalties (Summary)
            # Iterate 'summary' -> 'penalties'
            # Structure: data['summary']['penalties'] -> list of periods -> list of penalties
            penalties = data.get('summary', {}).get('penalties', [])
            
            home_pen = 0
            away_pen = 0
            home_pim = 0
            away_pim = 0
            
            for period in penalties:
                for pen in period.get('penalties', []):
                    mins = pen.get('duration', 0)
                    team_type = pen.get('teamAbbrev', {}).get('default')
                    
                    if team_type == home_team:
                        home_pen += 1
                        home_pim += mins
                    elif team_type == away_team:
                        away_pen += 1
                        away_pim += mins
            
            # 2. Officials (Often at bottom of landing)
            # Usually data['gameInfo']['referees'] ?
            # Or data['officials']
            # Revisit: Landing often lacks officials. Boxscore often lacks officials.
            # The 'RightRail' or 'Gamecenter' used to have them.
            # Actually, standard key in Landing is often missing.
            # Let's check `summary` -> `gameInfo`?
            # Valid Key: `data['summary']['gameInfo']['referees']`
            # Wait, let's keep it simple. If we can't find refs, we can't do V2.
            # I will try to extract whatever officials I can find.
            
            # Let's try collecting keys
            refs = []
            # summary = data.get('summary', {}) # Not usually there
            # check root
            # Referees are usually not in Landing directly.
            # THEY ARE IN BOXSCORE! https://api-web.nhle.com/v1/game/{id}/boxscore
            # Let's revert to Boxscore for Refs + Landing for Penalties?
            # Or verify Boxscore has Penalties? Yes, Boxscore has 'playerByGameStats' but maybe not summary.
            
            # OK, let's try Boxscore URL again.
            return self.fetch_actual_boxscore(game_id, home_team, away_team)
            
        except Exception:
            return None

    def fetch_game_boxscore(self, game_id):
        return self.fetch_game_landing(game_id)

    def fetch_game_landing(self, game_id):
        url = f"{self.base_url}/game/{game_id}/landing"
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code != 200: 
                print(f"❌ Landing Fetch Failed for {game_id}: Status {r.status_code} | URL: {url}")
                return None
            data = r.json()
            
            # DEBUG: Dump Landing
            if not os.path.exists("debug_landing.json"):
                import json
                with open("debug_landing.json", "w") as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved debug_landing.json for {game_id}")

            # 1. Teams
            h_team = data.get('homeTeam', {}).get('abbrev')
            a_team = data.get('awayTeam', {}).get('abbrev')

            # 2. Officials (Check 'summary' -> 'gameInfo' -> 'referees' or root 'officials')
            # Note: API V1 structure varies. Let's look for officials in common places.
            # Often it does NOT have officials in landing. We might need RIGHT RAIL.
            # But let's check debug_landing.json to be sure. 
            # For now, return None if we can't verify structure, relying on the debug dump to guide the next fix.
            
            # Temporary: Return empty just to generate the debug file
            return None # We need to inspect the JSON first
            
        except Exception as e:
            print(f"❌ Error fetching landing: {e}")
            return None

if __name__ == "__main__":
    client = NHLRefClient()
    # Test just 1 week for speed
    client.fetch_season_logs(start_date="2025-10-07", end_date="2025-10-14")
