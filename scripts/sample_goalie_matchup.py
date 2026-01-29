import sys
import os
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from features_nhl import GoalieGameMap

def sample_matchup():
    mapper = GoalieGameMap()
    
    # Get unique game IDs
    unique_games = mapper.df['gameId'].unique()
    
    if len(unique_games) == 0:
        print("No games found!")
        return

    # Pick a random game
    random_game_id = random.choice(unique_games)
    
    # Get rows for this game to find Date vs Teams
    game_rows = mapper.df[mapper.df['gameId'] == random_game_id]
    game_date = game_rows.iloc[0]['gameDate']
    teams = game_rows['teamAbbrev'].unique()
    
    print(f"\n🎲 Random Game Verification Sample")
    print(f"=======================================")
    print(f"📅 Date:   {game_date}")
    print(f"🆔 GameID: {random_game_id}")
    print(f"⚔️  Start:  {teams[0]} vs {teams[1] if len(teams) > 1 else '???'}")
    print(f"---------------------------------------")
    
    for team in teams:
        starter = mapper.get_starter(random_game_id, team)
        print(f"🥅 {team} Starter: {starter}")
        
    print(f"=======================================\n")

if __name__ == "__main__":
    sample_matchup()
