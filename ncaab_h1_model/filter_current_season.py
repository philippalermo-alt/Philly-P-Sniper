"""
Filter historical games to current season (2025-26) only.
Removes games from previous seasons to prevent training on old rosters.
"""

import json
from collections import Counter

def filter_current_season():
    """Filter games to 2025-26 season only based on ESPN game IDs."""

    # Load existing data
    print("Loading historical games...")
    with open('data/historical_games.json', 'r') as f:
        all_games = json.load(f)

    print(f"Total games before filtering: {len(all_games)}")

    # ESPN game ID prefixes for 2025-26 season
    # Based on analysis: 401826xxx and higher are current season
    # 401804xxx - 401824xxx are previous season
    CURRENT_SEASON_THRESHOLD = 401826000

    # Filter games
    current_season_games = []
    old_season_games = []

    for game in all_games:
        game_id = int(game.get('game_id', 0))

        if game_id >= CURRENT_SEASON_THRESHOLD:
            current_season_games.append(game)
        else:
            old_season_games.append(game)

    print(f"\n📊 Filtering Results:")
    print(f"  2025-26 season games: {len(current_season_games)}")
    print(f"  Previous season games (removed): {len(old_season_games)}")

    # Show game ID distribution
    prefix_counts = Counter()
    for game in current_season_games:
        gid = str(game.get('game_id', ''))
        if len(gid) >= 6:
            prefix_counts[gid[:6]] += 1

    print(f"\n📅 Current season game ID distribution:")
    for prefix, count in sorted(prefix_counts.items())[:10]:
        print(f"  {prefix}xxx: {count} games")

    # Backup old data
    print(f"\n💾 Creating backup...")
    with open('data/historical_games_BACKUP.json', 'w') as f:
        json.dump(all_games, f, indent=2)
    print(f"  Backed up to: data/historical_games_BACKUP.json")

    # Save filtered data
    print(f"\n✅ Saving filtered data...")
    with open('data/historical_games.json', 'w') as f:
        json.dump(current_season_games, f, indent=2)

    print(f"  Saved {len(current_season_games)} current season games")

    # Now rebuild team profiles with current season only
    print(f"\n🔄 Rebuilding team profiles...")
    from ncaab_h1_scraper import NCAAB_H1_Scraper

    scraper = NCAAB_H1_Scraper()
    profiles = scraper.build_team_profiles(current_season_games)

    # Save updated profiles
    with open('data/team_h1_profiles.json', 'w') as f:
        json.dump(profiles, f, indent=2)

    print(f"  Updated profiles for {len(profiles)} teams")

    print(f"\n✨ Done! Data filtered to 2025-26 season only.")
    print(f"\nNext steps:")
    print(f"  1. python ncaab_h1_train.py  # Retrain model")
    print(f"  2. Check if Test MAE improves (expect 6.5-7.5 points)")

if __name__ == "__main__":
    filter_current_season()
