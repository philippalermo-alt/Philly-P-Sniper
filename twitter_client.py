
import tweepy
from config import Config
from utils import log
from budget_manager import budget

class TwitterClient:
    def __init__(self):
        self.client = None
        self.api = None
        
        # Check if keys are present
        if not (Config.TWITTER_CONSUMER_KEY and Config.TWITTER_CONSUMER_SECRET and 
                Config.TWITTER_ACCESS_TOKEN and Config.TWITTER_ACCESS_TOKEN_SECRET):
            log("TWITTER", "❌ Credentials missing from config. Twitter disabled.")
            return

        try:
            # Debug Keys
            log("TWITTER", f"Consumer Key: {Config.TWITTER_CONSUMER_KEY[:4]}***")
            
            # V2 Client (User Context - WRITE)
            self.client = tweepy.Client(
                consumer_key=Config.TWITTER_CONSUMER_KEY,
                consumer_secret=Config.TWITTER_CONSUMER_SECRET,
                access_token=Config.TWITTER_ACCESS_TOKEN,
                access_token_secret=Config.TWITTER_ACCESS_TOKEN_SECRET
            )
            
            # V1.1 Client (Fallback/Media)
            auth = tweepy.OAuth1UserHandler(
                Config.TWITTER_CONSUMER_KEY, Config.TWITTER_CONSUMER_SECRET,
                Config.TWITTER_ACCESS_TOKEN, Config.TWITTER_ACCESS_TOKEN_SECRET
            )
            self.api = tweepy.API(auth)
            
            # V2 Client (App Context - READ)
            self.client_read = tweepy.Client(bearer_token=Config.TWITTER_BEARER_TOKEN)
            
            log("TWITTER", "✅ Twitter Client Initialized (Hybrid Auth)")
            
        except Exception as e:
            log("TWITTER", f"❌ Initialization Error: {e}")

    def post_tweet(self, text):
        """
        Post a tweet to the authenticated account.
        """
        if not self.client:
            log("TWITTER", "❌ Client not authenticated. Cannot tweet.")
            return False

        if not budget.can_spend("tweets_sent"):
            return False

        try:
            # Twitter V2 API uses create_tweet
            response = self.client.create_tweet(text=text)
            log("TWITTER", f"🐦 Tweet Sent! ID: {response.data['id']}")
            budget.record_spend("tweets_sent")
            return True
        except Exception as e:
            log("TWITTER", f"⚠️ V2 Post Failed: {e}. Trying V1.1...")
            try:
                if self.api:
                    self.api.update_status(text)
                    log("TWITTER", "🐦 Tweet Sent via V1.1!")
                    budget.record_spend("tweets_sent")
                    return True
            except Exception as e2:
                log("TWITTER", f"❌ V1.1 Post Failed: {e2}")
                return False

    def follow_user(self, username=None, user_id=None):
        """
        Follow a user by username or ID.
        """
        if not self.client:
            log("TWITTER", "❌ Client not authenticated.")
            return False
            
        if not budget.can_spend("interactions"):
            return False

        try:
            if username and not user_id:
                if not budget.can_spend("users_read"):
                    return False
                
                # Use Bearer Token (client_read) for lookup to avoid 401
                if self.client_read:
                    user = self.client_read.get_user(username=username)
                else:
                    user = self.client.get_user(username=username)

                budget.record_spend("users_read")
                
                if user.data:
                    user_id = user.data.id
                else:
                    log("TWITTER", f"❌ Could not resolve username: {username}")
                    return False
            
            if user_id:
                self.client.follow_user(user_id)
                log("TWITTER", f"✅ Followed user ID: {user_id}")
                budget.record_spend("interactions")
                return True
                
        except Exception as e:
            log("TWITTER", f"❌ Follow Failed: {e}")
            return False

    def like_tweet(self, tweet_id):
        """
        Like a specific tweet.
        """
        if not self.client:
            return False
            
        if not budget.can_spend("interactions"):
            return False

        try:
            self.client.like(tweet_id)
            log("TWITTER", f"❤️ Liked tweet: {tweet_id}")
            budget.record_spend("interactions")
            return True
        except Exception as e:
            log("TWITTER", f"❌ Like Failed: {e}")
            return False

    def retweet(self, tweet_id):
        """
        Retweet a specific tweet.
        """
        if not self.client:
            return False

        if not budget.can_spend("tweets_sent"): # Retweets count as Tweets usually? Or interactions? 
            # Logic: Retweets are posts.
            return False

        try:
            self.client.retweet(tweet_id)
            log("TWITTER", f"🔁 Retweeted: {tweet_id}")
            budget.record_spend("tweets_sent")
            return True
        except Exception as e:
            log("TWITTER", f"❌ Retweet Failed: {e}")
            return False

if __name__ == "__main__":
    # Test Script
    bot = TwitterClient()
    bot.post_tweet(f"🤖 Philly Edge: AI is online. #PhillyEdge #Test")
