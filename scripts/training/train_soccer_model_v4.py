"""
Soccer Model Trainer V4 (The "Gold Standard" Attempt)
-----------------------------------------------------
Improvements:
1. League Baseline uses xG (Apples-to-Apples).
2. Tracks Defensive Form (xG Against) explicitly.
3. Explicit 'exp_total_xg' feature for the Tree.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV
import pickle
from database import get_db

class SoccerModelTrainerV4:
    def __init__(self):
        self.model = None
        self.features = [
            'home_att_h', 'home_def_h', 
            'away_att_a', 'away_def_a',
            'exp_total_xg',   # Explicit Sum
            'league_avg_xg',  # Context (xG based)
            'home_form_att', 'home_form_def', # Recent 5 games (Home)
            'away_form_att', 'away_form_def'  # Recent 5 games (Away)
        ]
        self.target = 'over_2_5'
        
        # Hyperparams
        self.alpha_long = 0.15  # Span ~13 games
        self.alpha_short = 0.30 # Span ~6 games (Form)
        
    def load_and_engineer(self):
        print("📥 Loading matches (V4)...")
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
        teams = {}
        leagues = {} # {League: RollingAvgTotalxG}
        
        def get_team_state(t):
            if t not in teams:
                # Initialize with league average ~2.70 total (1.35 each side)
                teams[t] = {
                    'home_att': 1.35, 'home_def': 1.35,
                    'away_att': 1.35, 'away_def': 1.35,
                    'recent_att': 1.35, 'recent_def': 1.35
                }
            return teams[t]
            
        def get_league_avg(l):
            return leagues.get(l, 2.70) # Default Total xG

        training_rows = []
        
        print("🔄 Running V4 Feature Loop...")
        
        for _, row in raw_df.iterrows():
            h, a = row['home_team'], row['away_team']
            lg = row['league']
            
            # 1. SNAPSHOT (Pre-Match)
            h_state = get_team_state(h)
            a_state = get_team_state(a)
            lg_avg = get_league_avg(lg)
            
            # Expected Goals calculation
            exp_h = (h_state['home_att'] + a_state['away_def']) / 2
            exp_a = (a_state['away_att'] + h_state['home_def']) / 2
            exp_total = exp_h + exp_a
            
            feat = {
                'home_att_h': h_state['home_att'],
                'home_def_h': h_state['home_def'],
                'away_att_a': a_state['away_att'],
                'away_def_a': a_state['away_def'],
                'exp_total_xg': exp_total,
                'league_avg_xg': lg_avg,
                
                # Form Deltas (Attacking Form vs Long Term, Defensive Form vs Long Term)
                'home_form_att': h_state['recent_att'] - h_state['home_att'],
                'home_form_def': h_state['recent_def'] - h_state['home_def'],
                'away_form_att': a_state['recent_att'] - a_state['away_att'],
                'away_form_def': a_state['recent_def'] - a_state['away_def'],
                
                'over_2_5': 1 if (row['home_goals'] + row['away_goals']) > 2.5 else 0
            }
            training_rows.append(feat)
            
            # 2. UPDATE (Post-Match)
            h_xg, a_xg = row['home_xg'], row['away_xg']
            
            if pd.notna(h_xg) and pd.notna(a_xg):
                total_xg = h_xg + a_xg
                
                # Home Update (At Home)
                # Att: Produced h_xg. Def: Allowed a_xg.
                teams[h]['home_att'] = (1 - self.alpha_long) * teams[h]['home_att'] + self.alpha_long * h_xg
                teams[h]['home_def'] = (1 - self.alpha_long) * teams[h]['home_def'] + self.alpha_long * a_xg
                
                # Home Form (Venue Agnostic for Form? Or Split? Let's keep separate "Recent" bucket that mixes venues)
                # Actually user said "recent_xg_for" and "recent_xg_against". 
                # Let's say "recent_att" updates on whatever they produced (h_xg)
                teams[h]['recent_att'] = (1 - self.alpha_short) * teams[h]['recent_att'] + self.alpha_short * h_xg
                teams[h]['recent_def'] = (1 - self.alpha_short) * teams[h]['recent_def'] + self.alpha_short * a_xg
                
                # Away Update (At Away)
                teams[a]['away_att'] = (1 - self.alpha_long) * teams[a]['away_att'] + self.alpha_long * a_xg
                teams[a]['away_def'] = (1 - self.alpha_long) * teams[a]['away_def'] + self.alpha_long * h_xg
                
                teams[a]['recent_att'] = (1 - self.alpha_short) * teams[a]['recent_att'] + self.alpha_short * a_xg
                teams[a]['recent_def'] = (1 - self.alpha_short) * teams[a]['recent_def'] + self.alpha_short * h_xg
                
                # League Update (Apple-to-Apple: Use xG totals)
                if lg not in leagues: leagues[lg] = 2.70
                leagues[lg] = 0.99 * leagues[lg] + 0.01 * total_xg
        
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
        
        print(f"🤖 Training V4 on {len(X_train)} matches...")
        
        # Slightly deeper tree allowed given better features
        self.model = xgb.XGBClassifier(
            max_depth=4,
            learning_rate=0.03,
            n_estimators=600,
            subsample=0.75,
            colsample_bytree=0.8,
            gamma=1  # Regularization
        )
        self.model.fit(X_train, y_train)
        
        calib = CalibratedClassifierCV(self.model, method='isotonic', cv=3)
        calib.fit(X_train, y_train)
        self.model_calib = calib
        
        # Eval
        preds_proba = self.model_calib.predict_proba(X_test)[:, 1]
        preds_class = (preds_proba > 0.5).astype(int)
        
        auc = roc_auc_score(y_test, preds_proba)
        brier = brier_score_loss(y_test, preds_proba)
        
        from sklearn.metrics import classification_report, confusion_matrix
        
        print("\n" + "="*50)
        print("📊 V4 FINAL RESULTS (Holdout Set)")
        print("="*50)
        print(f"AUC Score:   {auc:.4f}")
        print(f"Brier Score: {brier:.4f}")
        print("-" * 30)
        print("Classification Report:")
        print(classification_report(y_test, preds_class))
        print("-" * 30)
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, preds_class))
        
        # Feature Importance (Proxy from base model)
        print("-" * 30)
        print("Feature Importance (Gain):")
        importances = self.model.feature_importances_
        feature_names = self.features
        feat_imp = pd.DataFrame({'feature': feature_names, 'importance': importances})
        feat_imp = feat_imp.sort_values('importance', ascending=False)
        print(feat_imp)
        print("="*50)
        
        # Save
        with open('soccer_model_v4.pkl', 'wb') as f:
            pickle.dump(self.model_calib, f)
        print("\n✅ Saved soccer_model_v4.pkl")

if __name__ == "__main__":
    t = SoccerModelTrainerV4()
    df = t.load_and_engineer()
    if not df.empty:
        t.train(df)
