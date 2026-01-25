"""
Soccer Model Trainer V2 (Time-Aware)
------------------------------------
Prevents data leakage by calculating rolling features chronologically.
Features are frozen PRE-MATCH.
Updates occur POST-MATCH.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
import pickle
import os
from database import get_db

class SoccerModelTrainerV2:
    def __init__(self):
        self.model = None
        self.features = [
            'home_attack', 'home_defense',
            'away_attack', 'away_defense',
            'xg_diff', 'total_exp_xg'
        ]
        self.target = 'over_2_5'
        
        # Hyperparams for EWMA
        self.span = 10 
        self.alpha = 2 / (self.span + 1)
        
        # League Average xG (approx)
        self.league_avg_xg = 1.35
        
    def load_and_engineer_data(self):
        print("📥 Loading matches from DB (Time-Sorted)...")
        conn = get_db()
        if not conn: return pd.DataFrame()
        
        # Get all completed matches with xG
        query = """
            SELECT date, home_team, away_team, home_xg, away_xg, home_goals, away_goals
            FROM matches 
            WHERE home_xg IS NOT NULL 
            ORDER BY date ASC
        """
        raw_df = pd.read_sql(query, conn)
        conn.close()
        
        if raw_df.empty:
            print("❌ No data found.")
            return pd.DataFrame()
            
        print(f"✓ Loaded {len(raw_df)} matches. Starting Feature Loop...")
        
        # --- Time-Aware Feature Loop ---
        # Tracking State
        team_stats = {} # {team_name: {'attack': 1.35, 'defense': 1.35}}
        
        def get_state(team):
            if team not in team_stats:
                team_stats[team] = {'attack': self.league_avg_xg, 'defense': self.league_avg_xg}
            return team_stats[team]
            
        training_rows = []
        
        for _, row in raw_df.iterrows():
            h_team = row['home_team']
            a_team = row['away_team']
            
            # 1. SNAPSHOT (Pre-Match Features)
            h_state = get_state(h_team)
            a_state = get_state(a_team)
            
            # Construct Feature Vector
            # We predict Home Goals based on Home Attack vs Away Defense
            # We predict Away Goals based on Away Attack vs Home Defense
            
            feat = {
                'home_attack': h_state['attack'],
                'home_defense': h_state['defense'],
                'away_attack': a_state['attack'],
                'away_defense': a_state['defense'],
                'xg_diff': h_state['attack'] - a_state['attack'], # Simple proxy
                'total_exp_xg': (h_state['attack'] + a_state['defense'])/2 + (a_state['attack'] + h_state['defense'])/2,
                
                # Targets
                'over_2_5': 1 if (row['home_goals'] + row['away_goals']) > 2.5 else 0
            }
            training_rows.append(feat)
            
            # 2. UPDATE STEP (Post-Match Learning)
            # Home Update
            # Attack Performance = Actual xG created
            # Defense Performance = Actual xG allowed (Away xG)
            
            # Using actual xG for updates (cleanest signal)
            h_xg_actual = row['home_xg']
            a_xg_actual = row['away_xg']
            
            if pd.notna(h_xg_actual) and pd.notna(a_xg_actual):
                # Home Updates
                team_stats[h_team]['attack'] = (1 - self.alpha) * team_stats[h_team]['attack'] + self.alpha * h_xg_actual
                team_stats[h_team]['defense'] = (1 - self.alpha) * team_stats[h_team]['defense'] + self.alpha * a_xg_actual
                
                # Away Updates
                team_stats[a_team]['attack'] = (1 - self.alpha) * team_stats[a_team]['attack'] + self.alpha * a_xg_actual
                team_stats[a_team]['defense'] = (1 - self.alpha) * team_stats[a_team]['defense'] + self.alpha * h_xg_actual
                
        # To DataFrame
        df_final = pd.DataFrame(training_rows)
        
        # Burn-in Period: Drop first ~200 matches where stats are settling
        df_final = df_final.iloc[200:].reset_index(drop=True)
        print(f"✓ Feature Engineering Complete. {len(df_final)} rows ready (after burn-in).")
        return df_final

    def train(self, df):
        X = df[self.features]
        y = df[self.target]
        
        # Time constraints: Train on first 80%, Test on last 20%
        # Data is already sorted by date from the DB query
        split = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]
        
        print(f"🤖 Training on {len(X_train)} matches...")
        
        # XGBoost Classifier
        self.model = xgb.XGBClassifier(
            max_depth=3,
            learning_rate=0.03, # Slower learning for stability
            n_estimators=500,
            eval_metric='logloss',
            subsample=0.8
        )
        self.model.fit(X_train, y_train)
        
        # Calibration
        calib = CalibratedClassifierCV(self.model, method='isotonic', cv=3)
        calib.fit(X_train, y_train)
        self.model_calib = calib
        
        return X_test, y_test
        
    def evaluate(self, X_test, y_test):
        preds = self.model_calib.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, preds)
        brier = brier_score_loss(y_test, preds)
        
        print("\n📊 Validated Performance (No Leakage):")
        print(f"AUC: {auc:.4f}")
        print(f"Brier: {brier:.4f}")
        return auc
        
    def save(self):
        with open('soccer_model_v2_clean.pkl', 'wb') as f:
            pickle.dump(self.model_calib, f)
        print("✅ Saved cleanly trained model to soccer_model_v2_clean.pkl")

if __name__ == "__main__":
    trainer = SoccerModelTrainerV2()
    df = trainer.load_and_engineer_data()
    if not df.empty:
        X_t, y_t = trainer.train(df)
        trainer.evaluate(X_t, y_t)
        trainer.save()
