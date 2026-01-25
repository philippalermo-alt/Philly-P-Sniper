
from nba_api.stats.endpoints import boxscoresummaryv2, leaguegamefinder
from nba_api.stats.static import teams
import pandas as pd

# 1. Find a Game ID from this season
# Celtics = 1610612738
print("🔍 Searching for recent Celtics games...")
gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=1610612738)
games = gamefinder.get_data_frames()[0]

# Filter for 2025-26 season (Season_ID usually starts with '2')
# Actually, let's just grab the most recent game
recent_game = games.iloc[0]
game_id = recent_game['GAME_ID']
game_date = recent_game['GAME_DATE']
matchup = recent_game['MATCHUP']

print(f"🏀 Found Game: {matchup} ({game_date}) ID: {game_id}")

# 2. Get Box Score Summary
print(f"🔍 Fetching BoxScoreSummaryV2 for {game_id}...")
box = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
datasets = box.get_data_frames()

# Usually:
# 0: GameSummary
# 1: OtherStats
# 2: Officials
# ...

for i, df in enumerate(datasets):
    print(f"\nDataFrame {i} Columns: {df.columns.tolist()}")
    if 'OFFICIAL_ID' in df.columns or 'FIRST_NAME' in df.columns:
        print("✅ Possible Officials Table found!")
        print(df)

