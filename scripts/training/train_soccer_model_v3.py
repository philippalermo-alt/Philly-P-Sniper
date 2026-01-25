"""
Soccer Model Trainer V3 (Venue Splits + Context)
------------------------------------------------
Improvements:
1. Tracks Home/Away performance separately (4 ratings per team).
2. Adds League Context (League Average Goals).
3. Adds Form (Recent 5-game trend).
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
import pickle
from database import get_db

class SoccerModelTrainerV3:
    def __init__(self):
        self.model = None
        self.features = [
            'home_att_h', 'home_def_h', # Home Team at Home
            'away_att_a', 'away_def_a', # Away Team at Away
            'exp_xg_h', 'exp_xg_a',     # Expected Goals based on matchups
            'league_avg_xg',            # Context
            'home_form', 'away_form'    # Recent Performance Delta
        ]
        self.target = 'over_2_5'
        
        # Hyperparams
        self.alpha_long = 0.15  # Span ~13 games
        self.alpha_short = 0.30 # Span ~6 games (Form)
        
    def load_and_engineer(self):
        print("📥 Loading matches (V3)...")
        conn = get_db()
        if not conn: return pd.DataFrame()
        
        query = """
            SELECT date, league, home_team, away_team, home_xg, away_xg, home_goals, away_goals
            FROM matches 
            WHERE home_xg IS NOT NULL 
            ORDER BY date ASC
        """
        raw_df = pd.read_sql(query, conn)
        conn.close()
        
        if raw_df.empty: return pd.DataFrame()
        
        # --- State Tracking ---
        # Structure: {Team: {
        #   'home_att': 1.35, 'home_def': 1.35, 
        #   'away_att': 1.35, 'away_def': 1.35,
        #   'recent_xg': 1.35 (Mixed venue form)
        # }}
        teams = {}
        leagues = {} # {League: RollingAvgGoals}
        
        def get_team_state(t):
            if t not in teams:
                # Initialize with league average if usually ~1.35
                teams[t] = {
                    'home_att': 1.35, 'home_def': 1.35,
                    'away_att': 1.35, 'away_def': 1.35,
                    'recent_xg': 1.35
                }
            return teams[t]
            
        def get_league_avg(l):
            return leagues.get(l, 2.75) # Default ~2.75 goals/match

        training_rows = []
        
        print("🔄 Running Chronological Feature Loop...")
        
        for _, row in raw_df.iterrows():
            h, a = row['home_team'], row['away_team']
            lg = row['league']
            
            # 1. SNAPSHOT (Pre-Match)
            h_stats = get_team_state(h)
            a_stats = get_team_state(a)
            lg_avg = get_league_avg(lg)
            
            # Expected Goals calculation
            # Home Exp = (Home Home Attack * Away Away Defense) / League Avg ? 
            # Simplified: Weighted Average of Ratings
            exp_h = (h_stats['home_att'] + a_stats['away_def']) / 2
            exp_a = (a_stats['away_att'] + h_stats['home_def']) / 2
            
            feat = {
                'home_att_h': h_stats['home_att'],
                'home_def_h': h_stats['home_def'],
                'away_att_a': a_stats['away_att'],
                'away_def_a': a_stats['away_def'],
                'exp_xg_h': exp_h,
                'exp_xg_a': exp_a,
                'league_avg_xg': lg_avg,
                # Form: Is their recent xG running hot compared to historical?
                'home_form': h_stats['recent_xg'] - h_stats['home_att'], 
                'away_form': a_stats['recent_xg'] - a_stats['away_att'],
                
                'over_2_5': 1 if (row['home_goals'] + row['away_goals']) > 2.5 else 0
            }
            training_rows.append(feat)
            
            # 2. UPDATE (Post-Match)
            h_xg, a_xg = row['home_xg'], row['away_xg']
            total_goals = row['home_goals'] + row['away_goals']
            
            if pd.notna(h_xg) and pd.notna(a_xg):
                # Update Home Team (At Home)
                # Att: Produced h_xg. Def: Allowed a_xg.
                teams[h]['home_att'] = (1 - self.alpha_long) * teams[h]['home_att'] + self.alpha_long * h_xg
                teams[h]['home_def'] = (1 - self.alpha_long) * teams[h]['home_def'] + self.alpha_long * a_xg
                teams[h]['recent_xg'] = (1 - self.alpha_short) * teams[h]['recent_xg'] + self.alpha_short * h_xg
                
                # Update Away Team (At Away)
                teams[a]['away_att'] = (1 - self.alpha_long) * teams[a]['away_att'] + self.alpha_long * a_xg
                teams[a]['away_def'] = (1 - self.alpha_long) * teams[a]['away_def'] + self.alpha_long * h_xg
                teams[a]['recent_xg'] = (1 - self.alpha_short) * teams[a]['recent_xg'] + self.alpha_short * a_xg
                
                # Update League Context
                if lg not in leagues: leagues[lg] = 2.75
                leagues[lg] = 0.99 * leagues[lg] + 0.01 * total_goals
        
        df = pd.DataFrame(training_rows)
        return df.iloc[300:] # Burn-in

    def train(self, df):
        split = int(len(df) * 0.8)
        train_df = df.iloc[:split]
        test_df = df.iloc[split:]
        
        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_test = test_df[self.features]
        y_test = test_df[self.target]
        
        print(f"🤖 Training V3 on {len(X_train)} matches...")
        
        self.model = xgb.XGBClassifier(
            max_depth=4,
            learning_rate=0.02,
            n_estimators=600,
            subsample=0.7,
            colsample_bytree=0.8
        )
        self.model.fit(X_train, y_train)
        
        calib = CalibratedClassifierCV(self.model, method='isotonic', cv=3)
        calib.fit(X_train, y_train)
        self.model_calib = calib
        
        # Eval
        preds = self.model_calib.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, preds)
        
        print(f"📊 V3 Results:\nAUC: {auc:.4f}")
        
        # Save
        with open('soccer_model_v3.pkl', 'wb') as f:
            pickle.dump(self.model_calib, f)
        print("✅ Saved soccer_model_v3.pkl")

if __name__ == "__main__":
    t = SoccerModelTrainerV3()
    df = t.load_and_engineer()
    if not df.empty:
        t.train(df)
