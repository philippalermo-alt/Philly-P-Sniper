import tweepy
from config import Config

def test_auth():
    # 1. Try V2 Client (User Context) - just to show it's there
    client = tweepy.Client(
        consumer_key=Config.TWITTER_CONSUMER_KEY,
        consumer_secret=Config.TWITTER_CONSUMER_SECRET,
        access_token=Config.TWITTER_ACCESS_TOKEN,
        access_token_secret=Config.TWITTER_ACCESS_TOKEN_SECRET
    )
    print("\n🔑 Testing Bearer Token...")
    bearer = "AAAAAAAAAAAAAAAAAAAAAB2q7AEAAAAAds76WIfaesuxUI6aKVVbTPrCM9s%3DMZZZxliO2HEblmFDo1sbWNPuN1cBWajOnyTN8qRXA6M17HRUcJ"
    client_app = tweepy.Client(bearer_token=bearer)
    
    try:
        user = client_app.get_user(username="ActionNetworkHQ")
        print(f"✅ Bearer get_user() SUCCESS. ID: {user.data.id}")
    except Exception as e:
        print(f"❌ Bearer get_user() FAILED: {e}")

if __name__ == "__main__":
    test_auth()
