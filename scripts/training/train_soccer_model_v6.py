"""
Soccer Model Trainer V6 (The Market Consensus Model)
----------------------------------------------------
Integrates "Gold Standard" Market Data:
1. Closing Total (2.5, 3.0, 3.5, etc.)
2. Market Implied Probability (Vig-Free)

Hypothesis: Market Odds contain massive information (injuries, lineups, motivation).
Mixing checks (xG) + balances (Market) should maximize AUC.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import pickle
from database import get_db
from train_soccer_model_v4 import SoccerModelTrainerV4

class SoccerModelTrainerV6(SoccerModelTrainerV4):
    def __init__(self):
        super().__init__()
        self.features = [
            'exp_total_xg',    # Internal Signal
            'league_avg_xg',   # Context
            'xg_imbalance',    # Game State
            'market_prob',     # Wisdom of Crowds (Vig-Free)
            'closing_total'    # The "Line" (2.5, 3.5, etc)
        ]
        
    def train(self, df):
        print(f"📥 Loaded {len(df)} total matches.")
        
        # 1. Filter for rows with Market Data
        df_clean = df.dropna(subset=['market_avg_over', 'market_avg_under', 'closing_total']).copy()
        print(f"📉 Filtered to {len(df_clean)} matches with historical odds.")
        
        if len(df_clean) < 500:
            print("❌ Not enough data for V6 training yet. Wait for backfill.")
            return

        # 2. Engineer V6 Features
        # Reconstruct V4/V5 basics first if not present (V4 parent does some, but we need V5 logic too)
        exp_h = (df_clean['home_att_h'] + df_clean['away_def_a']) / 2
        exp_a = (df_clean['away_att_a'] + df_clean['home_def_h']) / 2
        df_clean['xg_imbalance'] = abs(exp_h - exp_a)
        
        # Market Prob (Vig-Free)
        # Prob = (1/O) / (1/O + 1/U)
        inv_o = 1 / df_clean['market_avg_over']
        inv_u = 1 / df_clean['market_avg_under']
        df_clean['market_prob'] = inv_o / (inv_o + inv_u)
        
        # 3. Split
        split = int(len(df_clean) * 0.8)
        train_df = df_clean.iloc[:split]
        test_df = df_clean.iloc[split:]
        
        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_test = test_df[self.features]
        y_test = test_df[self.target]
        
        print(f"🤖 Training V6 (LogReg + Market) on {len(X_train)} matches...")
        
        # 4. Model (Logistic Regression with Scaling)
        # Scaling is essential now because closing_total (2.5) vs probs (0.5) vs xG (3.0)
        self.model = LogisticRegression(solver='liblinear')
        
        pipe = Pipeline([
            ('scaler', StandardScaler()),
            ('logreg', self.model)
        ])
        pipe.fit(X_train, y_train)
        
        # 5. Calibration
        self.model_calib = CalibratedClassifierCV(pipe, method='sigmoid', cv=3)
        self.model_calib.fit(X_train, y_train)
        
        # 6. Eval
        preds_proba = self.model_calib.predict_proba(X_test)[:, 1]
        
        auc = roc_auc_score(y_test, preds_proba)
        brier = brier_score_loss(y_test, preds_proba)
        
        print("\n" + "="*50)
        print(f"📊 V6 FINAL RESULTS (Market Data Enabled)")
        print("="*50)
        print(f"AUC Score:   {auc:.4f}")
        print(f"Brier Score: {brier:.4f}")
        print("-" * 30)
        print("Note: Threshold optimization removed. Production uses EV-based staking.")
        
        print("-" * 30)
        print("Coefficients (Scaled):")
        coefs = pipe.named_steps['logreg'].coef_[0]
        for name, coef in zip(self.features, coefs):
            print(f"{name}: {coef:.4f}")
        print("="*50)
        
        # Save
        with open('soccer_model_v6.pkl', 'wb') as f:
            pickle.dump(self.model_calib, f)
        print("\n✅ Saved soccer_model_v6.pkl")

if __name__ == "__main__":
    t = SoccerModelTrainerV6()
    # Note: load_and_engineer uses 'SELECT *' via read_sql in V4, so new columns might exist automatically?
    # V4 uses specific column list query. Need to check V4.
    # V4 Query: SELECT date, league, ... home_xg, away_xg ...
    # It does NOT select the new columns.
    # We must override load_and_engineer.
    
    # Actually, simpler to just override the query logic here or use 'SELECT *'
    
    # Monkey patch or Override
    class V6Full(SoccerModelTrainerV6):
        def load_and_engineer(self):
            conn = get_db()
            # Select ALL columns to get market data
            query = "SELECT * FROM matches WHERE home_xg IS NOT NULL ORDER BY date ASC"
            raw_df = pd.read_sql(query, conn)
            conn.close()
            
            # Run V4 Logic manually? 
            # V4 load_and_engineer returns 'df' with features.
            # But V4 logic is tightly coupled to its query.
            # We better copy-paste V4 logic or modify V4 file.
            # Modifying V4 file is risky for V4/V5 reproducibility.
            # I will use a custom load function here that reuses the logic.
            
            # Recopying V4 Logic for safety (it's short)
            teams = {}
            leagues = {}
            training_rows = []
            
            alpha_long = 0.15
            alpha_short = 0.30

            for _, row in raw_df.iterrows():
                h, a = row['home_team'], row['away_team']
                lg = row['league']
                
                # State Retrieve
                if h not in teams: teams[h] = {'home_att': 1.35, 'home_def': 1.35, 'away_att': 1.35, 'away_def': 1.35, 'recent_att': 1.35, 'recent_def': 1.35}
                if a not in teams: teams[a] = {'home_att': 1.35, 'home_def': 1.35, 'away_att': 1.35, 'away_def': 1.35, 'recent_att': 1.35, 'recent_def': 1.35}
                if lg not in leagues: leagues[lg] = 2.70
                
                h_state, a_state, lg_avg = teams[h], teams[a], leagues[lg]
                
                # Features
                exp_h = (h_state['home_att'] + a_state['away_def']) / 2
                exp_a = (a_state['away_att'] + h_state['home_def']) / 2
                exp_total = exp_h + exp_a
                
                # Append Row
                feat = {
                    'home_att_h': h_state['home_att'], 'home_def_h': h_state['home_def'],
                    'away_att_a': a_state['away_att'], 'away_def_a': a_state['away_def'],
                    'exp_total_xg': exp_total, 'league_avg_xg': lg_avg,
                    'home_form_att': h_state['recent_att'] - h_state['home_att'],
                    'home_form_def': h_state['recent_def'] - h_state['home_def'],
                    'away_form_att': a_state['recent_att'] - a_state['away_att'],
                    'away_form_def': a_state['recent_def'] - a_state['away_def'],
                    'over_2_5': 1 if (row['home_goals'] + row['away_goals']) > 2.5 else 0,
                    
                    # V6 NEW
                    'market_avg_over': row.get('market_avg_over'),
                    'market_avg_under': row.get('market_avg_under'),
                    'closing_total': row.get('closing_total')
                }
                training_rows.append(feat)
                
                # Update
                h_xg, a_xg = row['home_xg'], row['away_xg']
                if pd.notna(h_xg) and pd.notna(a_xg):
                    total_xg = h_xg + a_xg
                    teams[h]['home_att'] = (1 - alpha_long) * teams[h]['home_att'] + alpha_long * h_xg
                    teams[h]['home_def'] = (1 - alpha_long) * teams[h]['home_def'] + alpha_long * a_xg
                    teams[h]['recent_att'] = (1 - alpha_short) * teams[h]['recent_att'] + alpha_short * h_xg
                    teams[h]['recent_def'] = (1 - alpha_short) * teams[h]['recent_def'] + alpha_short * a_xg
                    
                    teams[a]['away_att'] = (1 - alpha_long) * teams[a]['away_att'] + alpha_long * a_xg
                    teams[a]['away_def'] = (1 - alpha_long) * teams[a]['away_def'] + alpha_long * h_xg
                    teams[a]['recent_att'] = (1 - alpha_short) * teams[a]['recent_att'] + alpha_short * a_xg
                    teams[a]['recent_def'] = (1 - alpha_short) * teams[a]['recent_def'] + alpha_short * h_xg
                    
                    leagues[lg] = 0.99 * leagues[lg] + 0.01 * total_xg

            return pd.DataFrame(training_rows).iloc[300:]

    t = V6Full()
    df = t.load_and_engineer()
    if not df.empty:
        t.train(df)
