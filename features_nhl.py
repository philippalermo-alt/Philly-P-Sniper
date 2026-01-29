import pandas as pd
import os
import glob

class GoalieGameMap:
    def __init__(self, data_dir="Hockey Data"):
        self.data_dir = data_dir
        self.df = self._load_all_seasons()
        
        # Pre-compute a lookup dictionary for O(1) access
        # Key: (gameId, teamAbbrev) -> Value: goalieFullName
        self.lookup = self._build_lookup()
        
    def _load_all_seasons(self):
        """Loads and concatenates goalie logs from all season folders."""
        all_files = glob.glob(os.path.join(self.data_dir, "*", "goalie_game_logs.csv"))
        if not all_files:
            print(f"⚠️  No goalie logs found in {self.data_dir}")
            return pd.DataFrame()
        
        dfs = []
        for f in all_files:
            try:
                # Ensure gameId is string to avoid float conversions
                df = pd.read_csv(f, dtype={'gameId': str, 'playerId': str})
                dfs.append(df)
            except Exception as e:
                print(f"❌ Error loading {f}: {e}")
                
        if not dfs:
            return pd.DataFrame()
            
        full_df = pd.concat(dfs, ignore_index=True)
        return full_df

    def _build_lookup(self):
        """
        Builds a dictionary for fast lookup.
        Logic:
        1. Filter for gamesStarted == 1 (The official starter).
        2. If multiple starters (data error), take the one with most TOI.
        3. If no starter listed (rare), take the one with most TOI.
        """
        if self.df.empty:
            return {}

        lookup = {}
        
        # Group by Game and Team
        grouped = self.df.groupby(['gameId', 'teamAbbrev'])
        
        for (game_id, team), group in grouped:
            # 1. Try to find the declared starter
            starters = group[group['gamesStarted'] == 1]
            
            if len(starters) == 1:
                goalie_name = starters.iloc[0]['goalieFullName']
            elif len(starters) > 1:
                # Multiple designated starters? Take max TOI
                goalie_name = starters.loc[starters['timeOnIce'].idxmax()]['goalieFullName']
            else:
                # No designated starter? Take max TOI (likely the starter)
                if not group.empty:
                    goalie_name = group.loc[group['timeOnIce'].idxmax()]['goalieFullName']
                else:
                    goals_name = None
            
            if goalie_name:
                lookup[(str(game_id), team)] = goalie_name
                
        return lookup

    def get_starter(self, game_id, team_abbrev):
        """Returns the specific starting goalie for a game."""
        return self.lookup.get((str(game_id), team_abbrev), None)

    def get_matchup_goalies(self, game_id):
        """Returns a dict of {team: goalie} for both teams in a game."""
        # Find all keys with this game_id
        matchup = {}
        # This is O(N) over keys without a specialized structure, but N is ~10k games.
        # For faster access we could duplicate the index. 
        # But efficiently: we usually know the teams when asking.
        # If we DON'T know the teams, we iterate.
        
        # Optimization: Map gameId -> list of (team, goalie)
        if hasattr(self, '_game_index'):
             return self._game_index.get(str(game_id), {})
             
        # Build on demand if needed, or just iterate (it's fast enough for 10k items)
        for (gid, team), goalie in self.lookup.items():
            if gid == str(game_id):
                matchup[team] = goalie
                
        return matchup

if __name__ == "__main__":
    # Self-Test
    print("🏒 Initializing GoalieGameMap...")
    mapper = GoalieGameMap()
    print(f"✅ Loaded {len(mapper.df)} rows.")
    print(f"✅ Indexed {len(mapper.lookup)} game-team info tuples.")
    
    # Test with a known game ID from inspection (2023021310 - Stuart Skinner)
    test_id = "2023021310"
    test_team = "EDM"
    starter = mapper.get_starter(test_id, test_team)
    print(f"\n🧪 Test Lookup for Game {test_id} ({test_team}):")
    print(f"   🥅 Starter: {starter}")
    
    # Validation Check
    assert starter == "Stuart Skinner", f"Expected Stuart Skinner, got {starter}"
    print("   ✅ Assertion Passed.")
