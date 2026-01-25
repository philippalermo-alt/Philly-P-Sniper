
import os
import time
from twitter_client import TwitterClient
from utils import log
from budget_manager import budget

# Target Accounts to Follow & Monitor
TARGET_ACCOUNTS = [
    'ActionNetworkHQ',
    'SportsInsights',
    'PropSwap',
    'BetMGM',
    'DraftKings',
    'FDSportsbook',
    'BleacherReport',
    'br_betting'
]

# Keywords that might trigger a Quote Retweet (Future Phase)
INTEL_KEYWORDS = [
    'ruled out',
    'injury report',
    'sharp money',
    'line movement',
    'late scratch'
]

class CommunityManager:
    def __init__(self):
        self.twitter = TwitterClient()
        self.my_id = None
        
        # Resolve own ID
        if self.twitter.client:
            try:
                me = self.twitter.client.get_me()
                if me.data:
                    self.my_id = me.data.id
                    log("COMMUNITY", f"✅ Identified as User ID: {self.my_id}")
            except Exception as e:
                log("COMMUNITY", f"❌ Failed to get own ID: {e}")

    def run_daily_tasks(self):
        """
        Run this once a day (e.g. 9 AM).
        """
        log("COMMUNITY", "🚀 Starting Daily Community Tasks...")
        
        report = {
            "mentions": [],
            "suggested_follows": [],
            "suggested_engagements": []
        }
        
        # 1. Check Mentions (Replies)
        mentions = self.get_mentions()
        if mentions:
            report["mentions"] = mentions
            log("COMMUNITY", f"✅ Found {len(mentions)} mentions.")

        # 2. Search for New Growth Targets (Hashtags)
        targets = self.search_growth_opportunities()
        if targets:
            report["suggested_follows"] = targets
            log("COMMUNITY", f"✅ Found {len(targets)} new targets.")
            
        # 3. Send Summary Email
        self.send_growth_report(report)
        
        log("COMMUNITY", "✅ Community Tasks Completed.")

    def get_mentions(self):
        """Get recent mentions using Bearer Token."""
        try:
            cli = self.twitter.client_read if hasattr(self.twitter, 'client_read') and self.twitter.client_read else self.twitter.client
            mentions = cli.get_users_mentions(id=self.my_id, max_results=20, tweet_fields=['created_at', 'author_id', 'text'])
            
            results = []
            if mentions and mentions.data:
                for tweet in mentions.data:
                    # Like if possible (Best effort)
                    self.twitter.like_tweet(tweet.id)
                    results.append({
                        "text": tweet.text,
                        "url": f"https://twitter.com/i/web/status/{tweet.id}"
                    })
            return results
        except Exception as e:
            log("COMMUNITY", f"❌ Error checking mentions: {e}")
            return []

    def search_growth_opportunities(self):
        """
        Search for high-value tweets/users in our niche.
        """
        if not hasattr(self.twitter, 'client_read') or not self.twitter.client_read:
            return []
            
        keywords = ["#GamblingTwitter", "#NBABets", "#SportsBettingPicks"]
        candidates = []
        
        try:
            # Search recent tweets (Bearer Token allows this)
            query = " OR ".join(keywords) + " -is:retweet lang:en"
            tweets = self.twitter.client_read.search_recent_tweets(
                query=query, 
                max_results=20, 
                tweet_fields=['created_at', 'public_metrics', 'author_id'],
                expansions=['author_id']
            )
            
            if tweets and tweets.data:
                users = {u.id: u for u in tweets.includes['users']}
                
                for tweet in tweets.data:
                    metrics = tweet.public_metrics
                    # Filter for engagement (Don't spam small accounts, find influencers)
                    if metrics['like_count'] > 5: 
                        author = users.get(tweet.author_id)
                        if author:
                            candidates.append({
                                "username": author.username,
                                "text": tweet.text,
                                "url": f"https://twitter.com/{author.username}/status/{tweet.id}",
                                "likes": metrics['like_count']
                            })
                            
            return candidates[:10] # Top 10
            
        except Exception as e:
            log("COMMUNITY", f"❌ Search failed: {e}")
            return []

    def send_growth_report(self, report):
        """Compile and send email via EmailNotifier."""
        if not report["mentions"] and not report["suggested_follows"]:
            return

        try:
            from email_notifier import EmailNotifier
            emailer = EmailNotifier()
            
            html_parts = ["<h2>🚀 Daily Growth Opportunities</h2>"]
            
            # Mentions Section
            if report["mentions"]:
                html_parts.append("<h3>🔔 New Mentions (Action Required)</h3><ul>")
                for m in report["mentions"]:
                    html_parts.append(f"<li>📝 <b>Tweet:</b> {m['text']}<br><a href='{m['url']}'>Reply Now</a></li>")
                html_parts.append("</ul>")
                
            # Growth Section
            if report["suggested_follows"]:
                html_parts.append("<h3>🤝 Recommend Engaging / Following</h3><ul>")
                for f in report["suggested_follows"]:
                    html_parts.append(f"<li>👤 <b>@{f['username']}</b> (Likes: {f['likes']})<br>📝 {f['text'][:100]}...<br><a href='{f['url']}'>View Tweet</a></li>")
                html_parts.append("</ul>")
            
            body = "".join(html_parts)
            
            emailer.send_email(
                subject="📈 Philly Edge: Daily Growth Report",
                body=body,
                is_html=True
            )
            log("COMMUNITY", "📧 Growth Report Email Sent.")
            
        except ImportError:
            log("COMMUNITY", "❌ EmailNotifier not found.")
        except Exception as e:
            log("COMMUNITY", f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    cm = CommunityManager()
    cm.run_daily_tasks()
