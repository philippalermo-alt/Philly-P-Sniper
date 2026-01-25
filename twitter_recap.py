
import psycopg2
from datetime import datetime, timedelta
from config import Config
import argparse

def generate_recap_tweet(dry_run=False):
    print("🐦 Generating Recap Tweet...")
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    conn = psycopg2.connect(Config.DATABASE_URL)
    cur = conn.cursor()
    
    # Query settled bets from yesterday
    # Query settled bets from yesterday that were actually tweeted
    query = """
        SELECT il.sport, il.outcome, il.user_stake, il.user_odds 
        FROM intelligence_log il
        JOIN posted_tweets pt ON il.event_id = pt.event_id
        WHERE date(il.kickoff) = %s 
        AND il.outcome IN ('WON', 'LOST', 'PUSH')
    """
    cur.execute(query, (yesterday,))
    rows = cur.fetchall()
    
    if not rows:
        print("❌ No bets found for yesterday.")
        return

    # Aggregates
    summary = {}
    total_units = 0.0
    wins, losses, pushes = 0, 0, 0
    
    for sport, outcome, stake, odds in rows:
        # Normalize Sport Name
        s_nice = "Misc"
        if "nba" in sport: s_nice = "NBA"
        elif "ncaab" in sport: s_nice = "CBB"
        elif "nfl" in sport: s_nice = "NFL"
        elif "nhl" in sport: s_nice = "NHL"
        elif "soccer" in sport: s_nice = "⚽️"
        
        if s_nice not in summary: summary[s_nice] = 0.0
        
        # Safe float conversion
        stake = float(stake) if stake is not None else 0.0
        odds = float(odds) if odds is not None else 1.0
        
        # Calculate Units (Assumes stake is in $, convert to 1u? Or just use raw amount?)
        # Let's use raw PnL
        pnl = 0.0
        if outcome == 'WON':
            pnl = stake * (odds - 1)
            wins += 1
        elif outcome == 'LOST':
            pnl = -stake
            losses += 1
        elif outcome == 'PUSH':
            pushes += 1
            
        summary[s_nice] += pnl
        total_units += pnl
        
    # Format Tweet
    # 📅 Yesterday's Recap
    # 🏀 NBA: +1.5u
    # ⚽️: -0.5u
    #
    # 💰 Total: +1.0u (3-1-0)
    # #GamblingTwitter
    
    lines = [f"📅 Recap {yesterday.strftime('%m/%d')}"]
    
    for s, pnl in summary.items():
        icon = "🟢" if pnl > 0 else "🔴"
        lines.append(f"{s}: {pnl:+.2f}u")
        
    lines.append("")
    lines.append(f"💰 Total: {total_units:+.2f}u ({wins}-{losses}-{pushes})")
    lines.append("#PhillyPSniper")
    
    tweet_text = "\n".join(lines)
    
    print("\n--- TWEET PREVIEW ---")
    print(tweet_text)
    print("---------------------\n")
    
    if not dry_run:
        try:
            from twitter_client import TwitterClient
            client = TwitterClient()
            # client.post_tweet(tweet_text) 
            print("⚠️ Posting Disabled (Safety Mode). Use --force to override if implemented.")
        except ImportError:
            print("❌ Tweepy/TwitterClient not found. Cannot post.")
    else:
        print("✅ Dry Run Complete.")

if __name__ == "__main__":
    generate_recap_tweet(dry_run=True)
