from api_clients import get_nhl_player_stats
import json

print("🏒 Fetching NHL Player Stats...")
stats = get_nhl_player_stats()

print(f"✅ Fetched {len(stats)} players.")

# Print top 5 by Total Shots
sorted_players = sorted(stats.items(), key=lambda x: x[1]['total_shots'], reverse=True)[:5]

print("\n🎯 Top 5 Shooters:")
for name, data in sorted_players:
    print(f"{name}: {data['total_shots']} shots ({data['avg_shots']:.2f}/game) - {data['games']} games")
