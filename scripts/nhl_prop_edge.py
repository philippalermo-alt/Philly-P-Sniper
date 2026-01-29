
import sys
import os
from datetime import datetime
from db.connection import get_db
from data.clients.odds_api import fetch_prop_odds
from scripts.nhl_edge_model import NHLEdgeModel
from unidecode import unidecode

# Config
MIN_EDGE = 0.02 # 2% Edge
SPORT_KEY = "icehockey_nhl"

class NHLEdgeRunner:
    def __init__(self):
        print("🏒 Init NHL Edge Runner...")
        self.model = NHLEdgeModel() 
        self.found = 0
        
    def run(self):
        print("📡 Fetching Odds...")
        # Markets: Points, Assists, Shots, Goals (Anytime + O/U)
        markets = "player_points,player_assists,player_shots_on_goal,player_goal_scorer_anytime,player_goals"
        odds_data = fetch_prop_odds(SPORT_KEY, markets=markets)
        
        if not odds_data:
            print("⚠️ No odds found.")
            return

        print(f"🔎 Analyzing {len(odds_data)} players...")
        
        for player_name, market_dict in odds_data.items():
            self.analyze_player(player_name, market_dict)
            
        print(f"✅ Run Complete. Found {self.found} +EV plays.")
        
    def analyze_player(self, player_name, market_dict):
        # 1. Check Model
        # We pass to calc_edge which handles lookup/Tier C checks
        # But efficiently, we should check projection first once.
        proj = self.model.get_projections(player_name)
        if not proj:
            # Try fuzzy/normalized name matching within model?
            return
            
        if not proj['priceable']:
            # Tier C Logic - Skip silently
            return 
            
        # 2. Iter Markets
        # Goals (Anytime)
        if 'player_goal_scorer_anytime' in market_dict:
            self.check_market(player_name, 'Goals', 0.5, market_dict['player_goal_scorer_anytime'])

        # Goals (O/U)
        if 'player_goals' in market_dict:
            self.check_lines(player_name, 'Goals', market_dict['player_goals'])
            
        # Shots (O/U)
        if 'player_shots_on_goal' in market_dict:
            self.check_lines(player_name, 'SOG', market_dict['player_shots_on_goal'])
            
        # Assists (O/U)
        if 'player_assists' in market_dict:
             self.check_lines(player_name, 'Assists', market_dict['player_assists'])
             
        # Points (O/U) - Note: OddsAPI might call it player_points
        if 'player_points' in market_dict:
             self.check_lines(player_name, 'Points', market_dict['player_points'])

    def check_lines(self, player, m_type, offers):
        # Offers is list of books/outcomes. We want 'Over'.
        if not isinstance(offers, list): return
        
        for offer in offers:
            if offer.get('side') != 'Over': continue
            
            line = float(offer.get('line', 0.5))
            price = float(offer.get('price'))
            book = offer.get('book')
            matchup = offer.get('matchup')
            kickoff = offer.get('commence_time')
            
            self.evaluate(player, m_type, line, price, book, matchup, kickoff)

    def check_market(self, player, m_type, line, offers):
        # For Anytime Goal, structure is usually a list of single outcomes (YES)
        if not isinstance(offers, list): return
        for offer in offers:
            # "Anytime Goal" implies Over 0.5.
            price = float(offer.get('price'))
            book = offer.get('book')
            matchup = offer.get('matchup')
            kickoff = offer.get('commence_time')
            
            self.evaluate(player, m_type, line, price, book, matchup, kickoff)

    def evaluate(self, player, m_type, line, price, book, matchup, kickoff):
        # Calc Edge
        result = self.model.calc_edge(player, m_type, line, price)
        if not result: return
        
        edge = result['edge']
        
        if edge >= MIN_EDGE:
            self.log_bet(player, m_type, line, price, edge, result['model_prob'], book, matchup, kickoff, result['tier'])
            self.found += 1
            
    def log_bet(self, player, m_type, line, price, edge, true_prob, book, matchup, kickoff, tier):
        conn = get_db()
        cur = conn.cursor()
        
        # Selection String
        if m_type == 'Goals':
            sel = f"{player} Anytime Goal"
        else:
            sel = f"{player} Over {line} {m_type}"
            
        # Tier Tag
        sel += f" [{tier}]"
        
        # Unique ID
        slug = f"NHL_{player}_{m_type}_{line}_{datetime.now().strftime('%Y%m%d')}"
        
        # Insert
        sql = """
            INSERT INTO intelligence_log 
            (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, book, outcome, user_bet)
            VALUES 
            (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', FALSE)
            ON CONFLICT (event_id) DO UPDATE SET
            edge = EXCLUDED.edge, true_prob = EXCLUDED.true_prob, odds = EXCLUDED.odds
        """
        try:
            cur.execute(sql, (
                slug,
                kickoff,
                "Hockey",
                matchup,
                sel,
                float(price),
                float(true_prob * 100), # Cast to float
                float(edge),            # Cast to float
                book
            ))
            conn.commit()
            print(f"  💰 Found: {sel} ({price}) Edge: {edge*100:.1f}%")
        except Exception as e:
            print(f"  ❌ DB Log Error: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    runner = NHLEdgeRunner()
    runner.run()
