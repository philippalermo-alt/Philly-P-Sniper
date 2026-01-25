from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.static import teams
import pandas as pd
import time

class NBADvPClient:
    """
    Client for fetching NBA Defense vs Position (DvP) and general defensive metrics.
    Uses nba_api (official NBA stats).
    """
    def __init__(self):
        self.teams = teams.get_teams()
        self.team_map = {t['full_name']: t['id'] for t in self.teams}

    def get_team_id(self, team_name):
        return self.team_map.get(team_name)

    def get_defense_stats(self, measure_type='Defense', per_mode='PerGame', date_to=None):
        """
        Fetch general team defensive stats (Opp Points, Steals, Blocks, Rating).
        Optional: date_to (MM/DD/YYYY) to fetch stats as of this date.
        """
        try:
            kwargs = {
                'measure_type_detailed_defense': measure_type if measure_type != 'Defense' else None,
                'per_mode_detailed': per_mode
            }
            if date_to:
                kwargs['date_to_nullable'] = date_to

            stats = leaguedashteamstats.LeagueDashTeamStats(**kwargs)
            df = stats.get_data_frames()[0]
            return df
        except Exception as e:
            print(f"Error fetching NBA Defense stats: {e}")
            return pd.DataFrame()

    def get_dvp_proxy(self):
        """
        Since exact DvP is hard to calculate without granular play-by-play parsing,
        we use Team Defensive Rating and Points Allowed as a proxy.
        """
        # Fetch Base stats (Wins, Losses, PTS, +/-)
        # Note: In NBA API, "Opponent Points" is usually strictly "PTS" in the Defense measure type?
        # Actually 'LeagueDashTeamStats' with measure_type='Base' gives PTS (scored).
        # We need 'Opponent' stats.
        
        # 'Defense' measure type gives: OREB, DREB, STL, BLK, REB, etc.
        # usually 'Opponent' columns are in specific dashboards.
        # Alternatively, use 'leaguedashteamstats' with measure_type='Opponent'.
        
        try:
            stats = leaguedashteamstats.LeagueDashTeamStats(measure_type_detailed_defense='Opponent', per_mode_detailed='PerGame')
            df = stats.get_data_frames()[0]
            # Rename for clarity
            df = df.rename(columns={'OPP_PTS': 'ALLOWED_PTS', 'OPP_FG_PCT': 'ALLOWED_FG_PCT'})
            return df[['TEAM_NAME', 'ALLOWED_PTS', 'ALLOWED_FG_PCT', 'OPP_TOV', 'OPP_BLK', 'OPP_STL']]
        except Exception as e:
            # Fallback to standard defense if Opponent specific fails
            print(f"Error fetching Opponent stats: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    client = NBADvPClient()
    print("Fetching NBA Defensive Stats...")
    df = client.get_dvp_proxy()
    if not df.empty:
        print(df.head())
    else:
        print("Failed to fetch data.")
