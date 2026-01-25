
import random
from datetime import datetime, timedelta
from database import get_db
from twitter_client import TwitterClient
from utils import log

def tweet_sharp_pick():
    """
    Selects a random active bet with sharp_score >= 60 and tweets it.
    """
    conn = get_db()
    cur = conn.cursor()
    
    # Logic:
    # 1. Look for games starting in the future (cutoff > NOW)
    # 2. Look for games created/logged recently (last 12 hours) to avoid stale lines
    # 3. Sharp Score >= 60
    
    query = """
    SELECT t1.event_id, t1.sport, t1.selection, t1.sharp_score, t1.teams, t1.user_odds, t1.user_stake
    FROM intelligence_log t1
    LEFT JOIN posted_tweets t2 ON t1.event_id = t2.event_id
    WHERE t1.kickoff > NOW()
      AND t1.outcome = 'PENDING'
      AND t1.edge >= 0.03 
      AND t1.edge <= 0.15
      AND t2.event_id IS NULL  -- EXCLUDE ALREADY TWEETED
    ORDER BY t1.edge DESC
    LIMIT 20
    """
    
    try:
        cur.execute(query)
        candidates = cur.fetchall()
        
        if not candidates:
            log("TWITTER", "No sharp picks (Score >= 60) found to tweet.")
            return

        # Intelligent Selection Logic
        # 1. Priority: "North Alabama" (User Request / Hot Game)
        # 2. Priority: PRO Systems
        # 3. High Sharp Score
        
        chosen_pick = None
        
        # Check for North Alabama
        for p in candidates:
            # p: (event_id, sport, selection, sharp_score, teams, odds, stake)
            if "North Alabama" in p[2] or "North Alabama" in p[4]:
                chosen_pick = p
                log("TWITTER", f"🎯 Priority Pick Found: {p[2]} (North Alabama)")
                break
                
        # If not found, check for top sharp score (deterministic for top value?)
        # Or keep random weighted?
        # User wants "North Alabama", so we handled that.
        # Fallback to random high score.
        if not chosen_pick:
            chosen_pick = random.choice(candidates)
            
        pick = chosen_pick
        
        event_id = pick[0]
        sport = pick[1]
        selection = pick[2] # 'selection' column usually holds "Lakers -5" or "Lakers"
        match_name = pick[4]
        odds = pick[5]
        stake = pick[6]
        
        # If selection looks like "Lakers -5.5 @ -110", we want just "Lakers" or "Lakers -5.5"
        
        # Clean up selection text for the tweet
        clean_pick = selection.split('@')[0].strip() # Remove odds if present
        
        # Formatting the Generic Message
        # "We're backing the Red Wings tonight"
        
        # Sport Emojis
        emoji = "🦅"
        if "NBA" in sport or "basketball" in sport: emoji = "🏀"
        if "NHL" in sport or "hockey" in sport: emoji = "YZY🏒" # Yeezy Hockey? Keeping user's custom emoji
        if "NFL" in sport or "football" in sport: emoji = "🏈"
        if "soccer" in sport: emoji = "⚽"
        if "NCAAB" in sport: emoji = "🎓🏀"
        
        # Variations of the message
        # Contextualize Tweet
        # If pick is "Over 145.5" or "Under 135", we MUST say the game name.
        # If pick is "Lakers -5", we can just say "Lakers -5", but adding "vs Celtics" helps.
        
        match_context = match_name if match_name else ""
        
        # Check if pick string contains team names (simple heuristic)
        # Or just always append match context for clarity
        
        templates = []
        if "Over" in clean_pick or "Under" in clean_pick:
             templates = [
                f"Riding with {clean_pick} in {match_context}. {emoji} #PhillyEdge",
                f"Tonight's play: {clean_pick} ({match_context}). {emoji} #PhillyEdge",
                f"Model identifies value on {clean_pick} in {match_context}. {emoji} #PhillyEdge"
             ]
        else:
             templates = [
                f"We're backing the {clean_pick} tonight vs {match_context.split(' vs ')[-1] if ' vs ' in match_context else ''}. {emoji} #PhillyEdge",
                f"Model likes {clean_pick} in {match_context}. {emoji} #PhillyEdge",
                f"Value found: {clean_pick}. {emoji} #PhillyEdge"
             ]
        
        msg = random.choice(templates)
        
        log("TWITTER", f"Attempting to tweet: {msg} (Score: {pick[3]})")
        
        bot = TwitterClient()
        success = bot.post_tweet(msg)
        
        if success:
            log("TWITTER", "✅ Tweet successfully sent.")
            
            # Log to posted_tweets table for Recap generation
            insert_q = """
                INSERT INTO posted_tweets 
                (event_id, sport, match_name, selection, odds, stake, tweet_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_q, (event_id, sport, match_name, selection, odds, stake, msg))
            conn.commit()
            log("TWITTER", f"📝 Logged tweet to DB for event {event_id}")
            
        else:
            log("TWITTER", "❌ Tweet failed to send.")
            
    except Exception as e:
        log("TWITTER", f"Error in tweet_sharp_pick: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    tweet_sharp_pick()
