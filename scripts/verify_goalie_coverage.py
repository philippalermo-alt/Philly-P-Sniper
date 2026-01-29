import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from features_nhl import GoalieGameMap
import pandas as pd

def verify_coverage():
    print("🕵️‍♂️ Starting Goalie Mapping Coverage Verification...")
    
    mapper = GoalieGameMap()
    
    # Get all unique game IDs from the underlying data
    # (Since we only have goalie logs, the set of gameIds in mapper.df IS the set of games we know about)
    # Ideally we would check against a 'schedule' or 'games' file, but checking internal consistency is a good first step.
    
    unique_games = mapper.df['gameId'].unique()
    total_games = len(unique_games)
    
    print(f"📊 Total Unique Games in Logs: {total_games}")
    
    mapped_count = 0
    missing_starters = []
    
    for game_id in unique_games:
        # Get teams involved in this game
        game_rows = mapper.df[mapper.df['gameId'] == game_id]
        teams = game_rows['teamAbbrev'].unique()
        
        game_fully_mapped = True
        
        for team in teams:
            starter = mapper.get_starter(game_id, team)
            if not starter:
                game_fully_mapped = False
                missing_starters.append(f"Game {game_id}: Missing starter for {team}")
        
        if game_fully_mapped:
            mapped_count += 1
            
    coverage_pct = (mapped_count / total_games) * 100
    
    print(f"\n✅ Games with Full Starter Info (Both Teams): {mapped_count} / {total_games}")
    print(f"🚀 Coverage Percentage: {coverage_pct:.2f}%")
    
    if missing_starters:
        print(f"\n⚠️  {len(missing_starters)} missing team-starters found. Sample:")
        for m in missing_starters[:10]:
            print(f"   - {m}")
    else:
        print("\n🎉 Perfect Coverage! Every team in every game has a starter.")

if __name__ == "__main__":
    verify_coverage()
