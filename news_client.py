import requests
import re
from datetime import datetime
import pandas as pd
from star_players import STAR_PLAYERS

class SentimentEngine:
    """
    V1 Sentiment Engine using robust keyword matching.
    """
    def __init__(self):
        self.negative_keywords = [
            'out', 'surgery', 'torn', 'sprain', 'doubtful', 'suspended', 
            'protocols', 'fracture', 'strain', 'concussion', 'miss', 'sidelined'
        ]
        # IMPROVEMENT: Step 4 - NBA Injury/Rest Scraper (GTD Logic)
        self.gtd_keywords = [
            'questionable', 'gtd', 'decision', 'uncertain', 'day-to-day', 'monitor'
        ]
        self.positive_keywords = [
            'return', 'available', 'cleared', 'probable', 'active', 'expect', 
            'healthy', 'upgraded'
        ]

    def analyze(self, text):
        """
        Returns (sentiment_score, badge, color, impact_value)
        Score: -1 (Negative), 1 (Positive), 0 (Neutral)
        Impact: Float (e.g. -0.05 for Star Out)
        """
        text_lower = text.lower()
        is_star = any(s.lower() in text_lower for s in STAR_PLAYERS)
        
        # Check Negative (OUT)
        for word in self.negative_keywords:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                if is_star:
                    return -1, "🔴 STAR OUT", "#B91C1C", -0.05 # -5% for Star
                return -1, "🟠 IMPACT OUT", "#EF4444", -0.015 # -1.5% for Role Player

        # Check GTD (Questionable)
        for word in self.gtd_keywords:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                if is_star:
                    return -0.5, "🟡 STAR GTD", "#EAB308", -0.02 # -2% for Star GTD
                return -0.5, "🟡 ROLE GTD", "#CA8A04", -0.005 # -0.5% for Role GTD
                
        # Check Positive
        for word in self.positive_keywords:
            if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
                if is_star:
                    return 1, "🟢 STAR RETURNS", "#059669", 0.03 # +3%
                return 1, "🟢 RETURNS", "#10B981", 0.01 # +1%
                
        return 0, "⚪ NEWS", "#94A3B8", 0.0

class NewsClient:
    """
    Fetches real-time news from ESPN Hidden APIs.
    """
    LEAGUE_URLS = {
        'NBA': 'http://site.api.espn.com/apis/site/v2/sports/basketball/nba/news',
        'NFL': 'http://site.api.espn.com/apis/site/v2/sports/football/nfl/news',
        'NHL': 'http://site.api.espn.com/apis/site/v2/sports/hockey/nhl/news',
        'NCAAB': 'http://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/news'
    }

    def __init__(self):
        self.sentiment = SentimentEngine()

    def fetch_news(self, league='NBA', limit=10):
        url = self.LEAGUE_URLS.get(league)
        if not url:
            return []

        try:
            resp = requests.get(url, params={'limit': limit}, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            articles = []
            for art in data.get('articles', []):
                headline = art.get('headline', '')
                desc = art.get('description', '')
                full_text = f"{headline}. {desc}"
                
                # Sentiment Analysis
                score, badge, color, impact = self.sentiment.analyze(full_text)
                
                # Extract Team ID if available (for mapping)
                team_id = None
                for cat in art.get('categories', []):
                    if cat.get('type') == 'team':
                        team_id = cat.get('teamId')
                        break
                
                articles.append({
                    'headline': headline,
                    'description': desc,
                    'published': art.get('published'),
                    'link': art.get('links', {}).get('web', {}).get('href'),
                    'team_id': team_id,
                    'sentiment_score': score,
                    'badge': badge,
                    'color': color,
                    'impact_value': impact,
                    'league': league
                })
                
            return articles

        except Exception as e:
            print(f"Error fetching {league} news: {e}")
            return []

    def get_all_news(self):
        """Fetches news for all supported leagues."""
        all_news = []
        for league in self.LEAGUE_URLS.keys():
            all_news.extend(self.fetch_news(league))
        
        # Sort by published date
        return sorted(all_news, key=lambda x: x['published'], reverse=True)

if __name__ == "__main__":
    client = NewsClient()
    news = client.fetch_news('NBA')
    for n in news:
        print(f"{n['badge']} {n['headline']}")
