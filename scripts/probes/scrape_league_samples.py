from understat_client import UnderstatClient
import time

def scrape_samples():
    client = UnderstatClient(headless=True)
    
    # 1. Get League Schedule
    print("--- Fetching EPL 2025 Schedule ---")
    matches = client.get_league_matches("EPL", "2025")
    
    completed_matches = [m for m in matches if m['is_result']]
    print(f"Total Matches: {len(matches)}")
    print(f"Completed Matches: {len(completed_matches)}")
    
    if not completed_matches:
        print("No completed matches found. Trying 2024 (current season).")
        matches = client.get_league_matches("EPL", "2024")
        completed_matches = [m for m in matches if m['is_result']]
        print(f"Total Matches (2024): {len(matches)}")
        print(f"Completed Matches (2024): {len(completed_matches)}")

    # 2. Scrape first 3 matches
    print("\n--- Scraping First 3 Completed Matches ---")
    for match in completed_matches[:3]:
        print(f"\nScraping Match ID: {match['id']} ({match['home_team']} vs {match['away_team']})")
        data = client.get_match_data(match['id'])
        
        if data:
            print(f"  > Match Info: {data['match_info']['team_h']} {data['match_info']['h_xg']} - {data['match_info']['a_xg']} {data['match_info']['team_a']}")
            print(f"  > Players Scraped: {len(data['players'])}")
            
            # Show top player
            top_player = max(data['players'], key=lambda x: x['xGChain'])
            print(f"  > Top Player (xGChain): {top_player['player']} ({top_player['xGChain']:.2f})")
        else:
            print("  > FAILED")
        
        time.sleep(1)

    client.quit()

if __name__ == "__main__":
    scrape_samples()
