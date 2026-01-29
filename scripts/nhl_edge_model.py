
import pandas as pd
import numpy as np
import os
from datetime import datetime
from scipy.stats import nbinom

# Frozen Parameters
ALPHA_SOG = 0.1395
ALPHA_AST = 0.1680

class NHLEdgeModel:
    def __init__(self, load_date=None):
        self.load_date = load_date or datetime.now().strftime('%Y-%m-%d')
        self.data = {}
        self._load_data()
        
    def _load_data(self):
        print(f"🏒 NHLEdgeModel: Loading Projections for {self.load_date}...")
        
        # Paths
        base = "data/nhl_processed"
        files = {
            'sog': f"{base}/sog_projections_phase1_nb.csv",
            'goals': f"{base}/goal_projections_phase2.csv",
            'assists': f"{base}/assist_projections_phase3.csv",
            'points': f"{base}/points_projections_phase4.csv"
        }
        
        # Load Phase 4 (Points) first - it contains the MASTER Tier/Eligibility logic
        if not os.path.exists(files['points']):
            print("❌ Points Projections not found.")
            return

        df_pts = pd.read_csv(files['points'])
        
        # Load Daily Projections if Available (Priority)
        daily_file = f"{base}/daily_projections.csv"
        if os.path.exists(daily_file):
            print(f"  Loaded Daily Projections from {daily_file}")
            df_daily = pd.read_csv(daily_file)
            # Daily Projections has date_str as column?
            # Check script: 'game_date' = date_str (YYYY-MM-DD).
            
            # Append Daily to df_pts
            # df_pts has historical. df_daily has today.
            # Concatenate
            df_pts = pd.concat([df_pts, df_daily], ignore_index=True)
            
        # Filter for Date
        # Note: CSV dates are typically YYYY-MM-DD.
        # We generally want to load ALL future games or just "Today's" games.
        # For efficiency, let's load everything >= Today.
        
        df_pts['game_date'] = pd.to_datetime(df_pts['game_date']).dt.strftime('%Y-%m-%d')
        current_data = df_pts[df_pts['game_date'] >= self.load_date].copy()
        
        # Create Lookup Dict: Key = (player_name_lower, game_date)
        self.points_lookup = {}
        for _, row in current_data.iterrows():
            key = (self._norm(row['player_name']), row['game_date'])
            self.points_lookup[key] = row.to_dict()
            
        print(f"  Loaded {len(current_data)} active projections from Points Engine.")
        
        # Load others for granularity if needed (SOG params)
        # SOG Mu is in Points CSV (`mu_sog`), so we don't necessarily need SOG CSV if Points CSV has it.
        # Points CSV columns: ['player_name', 'game_date', 'tier', 'is_priceable', 'mu_sog', 'p_goal', 'mu_ast', ...]
        # Yes, Points CSV has ALL primitive parameters needed for SOG/Goal/Assists/Points!
        # This is efficient. Phase 4 composes everything.
        
    def _norm(self, name):
        # normalize: lowercase, remove dots, strip
        return name.lower().replace(".", "").strip()
        
    def get_projections(self, player_name, game_date=None):
        """
        Returns full projection dict for a player on a date.
        If date is None, looks for first available match >= Today (assuming unique per day).
        """
        if not game_date:
            game_date = self.load_date
            
        key = (self._norm(player_name), game_date)
        row = self.points_lookup.get(key)
        
        if not row:
            # Fuzzy check or try without date?
            # For now strict.
            return None
            
        # TIER CHECK (Safeguard)
        # Tier C is blocked.
        if row.get('tier') == 'C':
            return {'priceable': False, 'reason': 'Tier C (Low Volume)'}
            
        return {
            'priceable': True,
            'tier': row['tier'],
            'mu_sog': row['mu_sog'],
            'mu_ast': row['mu_ast'],
            'p_goal': row['p_goal'], # Conversion prob
            
            # Pre-calced Probs (Phase 4)
            'prob_pts_1+': row['prob_points_1plus'],
            'prob_pts_2+': row['prob_points_2plus'],
            'mean_pts': row['proj_points_mean']
        }
        
    def calc_edge(self, player_name, market_type, line, odds_price):
        """
        Calculates Edge against a specific line/price.
        Market Types: 'SOG', 'Goals', 'Assists', 'Points'.
        """
        row = self.get_projections(player_name)
        if not row: return None
        if not row['priceable']: return None
        
        # 1. Calculate Model Probability for Line
        model_prob = 0.0
        
        if market_type == 'SOG':
            mu = row['mu_sog']
            # P(SOG > Line) = 1 - CDF(Line)
            # Line is typically X.5, so we want P(SOG >= ceil(Line)) 
            # e.g. Over 2.5 -> SOG >= 3.
            # CDF(k) is P(X <= k).
            # P(X > 2.5) = P(X >= 3) = 1 - P(X <= 2).
            # If line is 2.5, threshold k = 2.
            # If line is integer 3 (Over 3), pushes? NB usually handles discrete.
            # Books use .5 lines.
            
            threshold = int(line) # Over 2.5 -> threshold 2.
            # nbinom args: n, p.   n=1/alpha. p=n/(n+mu).
            n_p = 1.0 / ALPHA_SOG
            p_p = n_p / (n_p + mu)
            model_prob = 1.0 - nbinom.cdf(threshold, n_p, p_p)
            
        elif market_type == 'Goals':
            # Binomial / Composition
            # Simplified: Use Poisson/NB approx or just the stored P(1+)?
            # If line is 0.5 (Anytime Goal), use row['p_goal']? Assumes p_goal is P(Goal>=1)?
            # Check Phase 2 CSV. 'pred_prob_goal' is Conversion Rate per Shot.
            # 'prob_goal_1plus' is P(Goal>=1).
            # Points CSV doesn't have 'prob_goal_1plus' explicitly?
            # It has 'p_goal' (Conversion Rate). 
            # We need to re-calc P(Goal>=1) roughly: 
            # P(G>=1) ~= 1 - exp(-mu_sog * p_goal). (Poisson Approx).
            # Or use NB Mixture.
            # Better: Load Phase 2 CSV if strict accuracy needed.
            # For MVP, assume Poisson Approx is okay (slightly conservative).
            mu_g = row['mu_sog'] * row['p_goal']
            if line == 0.5:
                model_prob = 1.0 - np.exp(-mu_g)
            elif line == 1.5:
                # 1 - (P0 + P1)
                model_prob = 1.0 - np.exp(-mu_g) * (1 + mu_g)
                
        elif market_type == 'Assists':
            # Assist NB
            mu = row['mu_ast']
            threshold = int(line) # Over 0.5 -> 0.
            n_p = 1.0 / ALPHA_AST
            p_p = n_p / (n_p + mu)
            model_prob = 1.0 - nbinom.cdf(threshold, n_p, p_p)
            
        elif market_type == 'Points':
            if line == 0.5:
                model_prob = row['prob_pts_1+']
            elif line == 1.5:
                model_prob = row['prob_pts_2+']
            else:
                return None # Only modeling 0.5/1.5 in Sim results currently
        
        # 2. Convert Price to Implied Prob
        if odds_price > 0:
            implied = 100 / (odds_price + 100)
            dec = 1 + (odds_price / 100)
        else:
            implied = abs(odds_price) / (abs(odds_price) + 100)
            dec = 1 + (100 / abs(odds_price))
            
        edge = model_prob - implied
        return {
            'player': player_name,
            'market': f"{market_type} o{line}",
            'model_prob': model_prob,
            'implied_prob': implied,
            'edge': edge,
            'decimal_odds': dec,
            'tier': row['tier']
        }
