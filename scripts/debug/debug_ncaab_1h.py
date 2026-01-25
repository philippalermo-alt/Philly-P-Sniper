from probability_models import calculate_match_stats
from ratings import get_team_ratings
from config import Config

def debug_ncaab_game():
    print("🔍 Fetching Ratings...")
    ratings = get_team_ratings()
    
    # Debug Virginia vs North Carolina (Example from user report)
    # User said: Virginia Cavaliers vs North Carolina Tar Heels
    # Let's try to match them
    
    home = "Virginia Cavaliers"
    away = "North Carolina Tar Heels"
    
    # Check if they exist in ratings
    print(f"Checking '{home}'...")
    if home in ratings:
        print(f"✅ Found exact: {ratings[home]}")
    else:
        print("❌ Not found exact.")
        # Try finding key
        for k in ratings.keys():
            if "Virginia" in k and "West" not in k and "Common" not in k:
                print(f"   Potential match: {k}")

    print(f"Checking '{away}'...")
    if away in ratings:
        print(f"✅ Found exact: {ratings[away]}")
    else:
        print("❌ Not found exact.")
        for k in ratings.keys():
            if "Carolina" in k and "North" in k:
                print(f"   Potential match: {k}")

    # Manually select keys if needed (assuming standard names)
    # In ratings.py/KenPom, it's usually "Virginia" and "North Carolina"
    # User's input likely comes from Odds API which is "Virginia Cavaliers"
    
    # Let's run calculate_match_stats
    print("\n🧮 Running Calculation...")
    margin, total, std, sport = calculate_match_stats(
        home, away, ratings, 'NCAAB'
    )
    
    print(f"\n--- RESULTS for {home} vs {away} ---")
    print(f"Projected Margin: {margin}")
    print(f"Projected Total (Full Game): {total}")
    print(f"Std Dev: {std}")
    
    if total:
        print(f"1H Total (50%): {total * 0.50:.2f}")

    # User reported Pred 84.8
    # If 1H Total is 84.8, Full Game Total ~170.
    # If our result is ~130-140, then the inputs in the Real Run are different.
    
    # Also Check defaults
    print("\n--- Defaults Check ---")
    # If ratings missing
    m2, t2, s2, sp2 = calculate_match_stats("Hypothetical Missing Team", "Another Missing Team", ratings, 'NCAAB')
    print(f"Default Total: {t2}")
    
if __name__ == "__main__":
    debug_ncaab_game()
