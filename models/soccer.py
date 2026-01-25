import pandas as pd
import numpy as np
import pickle
import os
from db.connection import get_db

MODEL_PATH_V6 = "models/trained/soccer_model_v6.pkl"
MODEL_PATH_V5 = "models/trained/soccer_model_v5.pkl"

class SoccerModelV2:
    def __init__(self):
        self.model = None
        self.version = "V5"
        self.features = []
        
        self.team_stats = {}
        self.leagues = {}
        self.league_avg_xg = 2.70
        self.alpha_long = 0.15
        self.alpha_short = 0.30
        
        self.load_model()
        self.rebuild_hist_state()
        
    def load_model(self):
        force_v5 = os.getenv('FORCE_SOCCER_MODEL_V5', 'false').lower() == 'true'
        
        if os.path.exists(MODEL_PATH_V6) and not force_v5:
            print(f"✅ Loading V6 Model (Market Aware): {MODEL_PATH_V6}")
            with open(MODEL_PATH_V6, 'rb') as f:
                self.model = pickle.load(f)
            self.version = "V6"
            self.features = [
                'exp_total_xg', 'league_avg_xg', 'xg_imbalance', 
                'market_prob', 'closing_total'
            ]
        elif os.path.exists(MODEL_PATH_V5):
            print(f"⚠️ V6 not found. Loading V5 Model: {MODEL_PATH_V5}")
            with open(MODEL_PATH_V5, 'rb') as f:
                self.model = pickle.load(f)
            self.version = "V5"
            self.features = [
                'exp_total_xg', 'league_avg_xg', 'xg_imbalance'
            ]
        else:
            print("❌ No model found (V6 or V5). Train one first!")
            
    def rebuild_hist_state(self):
        """Replay history to build current Home/Away ratings (V4/V5 Logic)."""
        conn = get_db()
        if not conn: return
        
        query = """
            SELECT date, league, home_team, away_team, home_xg, away_xg, home_goals, away_goals
            FROM matches 
            WHERE home_xg IS NOT NULL 
            ORDER BY date ASC
        """
        try:
            df = pd.read_sql(query, conn)
        except Exception:
            conn.close()
            return
        conn.close()
        
        # Reset
        self.team_stats = {}
        self.leagues = {}
        
        def get_team_state(t):
            if t not in self.team_stats:
                self.team_stats[t] = {
                    'home_att': 1.35, 'home_def': 1.35,
                    'away_att': 1.35, 'away_def': 1.35,
                    # We still track form internally even if V5 doesn't use it yet (future proof)
                    'recent_att': 1.35, 'recent_def': 1.35 
                }
            return self.team_stats[t]

        for _, row in df.iterrows():
            h, a = row['home_team'], row['away_team']
            lg = row['league']
            
            get_team_state(h)
            get_team_state(a)
            if lg not in self.leagues: self.leagues[lg] = 2.70
            
            h_xg, a_xg = row['home_xg'], row['away_xg']
            
            if pd.notna(h_xg) and pd.notna(a_xg):
                total_xg = h_xg + a_xg
                
                # Update Home
                self.team_stats[h]['home_att'] = (1 - self.alpha_long) * self.team_stats[h]['home_att'] + self.alpha_long * h_xg
                self.team_stats[h]['home_def'] = (1 - self.alpha_long) * self.team_stats[h]['home_def'] + self.alpha_long * a_xg
                self.team_stats[h]['recent_att'] = (1 - self.alpha_short) * self.team_stats[h]['recent_att'] + self.alpha_short * h_xg
                self.team_stats[h]['recent_def'] = (1 - self.alpha_short) * self.team_stats[h]['recent_def'] + self.alpha_short * a_xg
                
                # Update Away
                self.team_stats[a]['away_att'] = (1 - self.alpha_long) * self.team_stats[a]['away_att'] + self.alpha_long * a_xg
                self.team_stats[a]['away_def'] = (1 - self.alpha_long) * self.team_stats[a]['away_def'] + self.alpha_long * h_xg
                self.team_stats[a]['recent_att'] = (1 - self.alpha_short) * self.team_stats[a]['recent_att'] + self.alpha_short * a_xg
                self.team_stats[a]['recent_def'] = (1 - self.alpha_short) * self.team_stats[a]['recent_def'] + self.alpha_short * h_xg
                
                # Update League
                self.leagues[lg] = 0.99 * self.leagues[lg] + 0.01 * total_xg
                
        print(f"✓ V5 State built for {len(self.team_stats)} teams.")

    def predict_match(self, home_team, away_team, league_name='Unknown', current_odds=None):
        """
        current_odds: dict {'over': 1.90, 'under': 1.90, 'line': 2.5}
        """
        if not self.model or not self.team_stats:
            return None
            
        h_state = self.team_stats.get(home_team, {
            'home_att': 1.35, 'home_def': 1.35
        })
        a_state = self.team_stats.get(away_team, {
            'away_att': 1.35, 'away_def': 1.35
        })
        lg_avg = self.leagues.get(league_name, 2.70)
        
        # Features (Pre-Match)
        exp_h = (h_state['home_att'] + a_state['away_def']) / 2
        exp_a = (a_state['away_att'] + h_state['home_def']) / 2
        exp_total = exp_h + exp_a
        xg_imbalance = abs(exp_h - exp_a)
        
        # V6 Market Data
        market_prob = 0.5
        closing_total = 2.5
        
        if current_odds:
            o = current_odds.get('over')
            u = current_odds.get('under')
            line = current_odds.get('line', 2.5)
            
            if o and u:
                # Vig-Free Prob
                inv_o = 1 / o
                inv_u = 1 / u
                market_prob = inv_o / (inv_o + inv_u)
            
            closing_total = line
            
        # Check if model expects V6 features
        # If model is V5/V5.2 pipeline, this might fail if we pass extra cols?
        # Actually Pipeline usually ignores extra cols if dataframe passed? 
        # No, sklearn requires exact cols.
        # We need to detect model version or try/catch.
        
        row_dict = {
            'exp_total_xg': exp_total,
            'league_avg_xg': lg_avg,
            'xg_imbalance': xg_imbalance
        }
        
        # Add V6 features if likely needed
        if 'market_prob' in self.features:
            row_dict['market_prob'] = market_prob
            row_dict['closing_total'] = closing_total
        
        feat_df = pd.DataFrame([row_dict])
        
        # Align columns
        feat_df = feat_df[self.features]
        
        prob_over = self.model.predict_proba(feat_df)[0][1]
        fair_odds = 1 / prob_over if prob_over > 0 else 99.0
        
        return {
            'home_team': home_team,
            'away_team': away_team,
            'market': 'Over 2.5 Goals',
            'prob_over': prob_over,
            'fair_odds': fair_odds,
            'exp_score': f"{exp_h:.2f} - {exp_a:.2f}",
            'exp_total_xg': exp_total
        }

if __name__ == "__main__":
    model = SoccerModelV2()
    res = model.predict_match("Liverpool", "Arsenal", "Premier League")
    if res:
        print(f"\n⚽ V5.2 Prediction: {res['home_team']} vs {res['away_team']}")
        print(f"   Total exp xG:   {res['exp_total_xg']:.2f}")
        print(f"   Over 2.5 Prob:  {res['prob_over']:.1%}")
        print(f"   Fair Odds:      {res['fair_odds']:.2f}")
