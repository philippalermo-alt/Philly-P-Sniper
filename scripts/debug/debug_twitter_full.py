
from twitter_client import TwitterClient
import tweepy

def debug_auth():
    print("🔍 Initializing Twitter Client...")
    bot = TwitterClient()
    
    if not bot.client:
        print("❌ Client failed to init")
        return

    print(f"🔑 ID: {bot.client.consumer_key[:5]}...")

    print("\n--- TEST 1: Get Me (Read Access) ---")
    try:
        me = bot.client.get_me(user_auth=True)
        print(f"✅ Success! ID: {me.data.id} | Name: {me.data.name}")
    except tweepy.Errors.TweepyException as e:
        print(f"❌ Failed: {e}")
        # Print full details if available
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response Status: {e.response.status_code}")
             print(f"   Response Text: {e.response.text}")
    except Exception as e:
        print(f"❌ Generic Error: {e}")

    print("\n--- TEST 2: Follow User (Write Access - Follow) ---")
    try:
        # Try to follow SportsCenter (ID: 26257166)
        bot.client.follow_user(target_user_id=26257166)
        print("✅ Success! Followed SportsCenter.")
    except tweepy.Errors.TweepyException as e:
        print(f"❌ Failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"   Response Status: {e.response.status_code}")
             print(f"   Response Text: {e.response.text}")

    print("\n--- TEST 3: Post Tweet (Write Access - Tweet) ---")
    # We know this works, but let's verify scope consistency
    print("ℹ️ Skipping to avoid spam, assuming working based on logs.")

if __name__ == "__main__":
    debug_auth()
