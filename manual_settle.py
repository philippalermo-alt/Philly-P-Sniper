from settle_props import settle_props
from processing.grading import settle_pending_bets, sync_calibration_log
from closing_line import fetch_closing_odds
# from tweet_picks import tweet_sharp_pick # User might want this manually?
# from daily_recap import generate_daily_recap

def main():
    print("📋 Starting Manual Settlement...")
    
    try:
        print("1. Settling Standard Wagers (ML, Spread, Total)...")
        settle_pending_bets()
    except Exception as e:
        print(f"❌ Standard Settle Error: {e}")

    try:
        print("2. Settling Props & Game Outcomes (Legacy Props)...")
        settle_props()
    except Exception as e:
        print(f"❌ Prop Settle Error: {e}")

    try:
        print("2. Fetching Closing Odds (CLV)...")
        fetch_closing_odds()
    except Exception as e:
        print(f"❌ CLV Error: {e}")

    try:
        print("4. Syncing Calibration Log (Self-Healing)...")
        sync_calibration_log()
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        
    print("✅ Settlement Complete.")

if __name__ == "__main__":
    main()
