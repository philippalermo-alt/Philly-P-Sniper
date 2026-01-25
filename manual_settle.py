from settle_props import settle_props
from closing_line import fetch_closing_odds
# from tweet_picks import tweet_sharp_pick # User might want this manually?
# from daily_recap import generate_daily_recap

def main():
    print("📋 Starting Manual Settlement...")
    try:
        print("1. Settling Props & Game Outcomes...")
        settle_props()
    except Exception as e:
        print(f"❌ Settle Error: {e}")

    try:
        print("2. Fetching Closing Odds (CLV)...")
        fetch_closing_odds()
    except Exception as e:
        print(f"❌ CLV Error: {e}")
        
    print("✅ Settlement Complete.")

if __name__ == "__main__":
    main()
