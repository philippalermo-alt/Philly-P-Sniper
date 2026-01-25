"""
Soccer ML Model Trainer (XGBoost + Logistic Regression)
Trains a binary classifier to predict Over 2.5 Goals using structural metrics.
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
from database import get_db

class SoccerModelTrainer:
    def __init__(self):
        self.model_xgb = None
        self.model_lr = None
        self.features = [
            'fragility_sum_top1xG', 'buildup_ratio', 'structural_balance',
            'xG_sum', 'shots_sum', 'chain_sum', 'buildup_sum', 'balance_xG_abs'
        ]
        self.target = 'over_2_5'

    def load_data(self):
        """Fetch match features from DB and constructing training set."""
        print("📥 Loading training data from database...")
        conn = get_db()
        if not conn:
            raise ConnectionError("Could not connect to database")

        query = """
            SELECT 
                home_team, away_team, 
                home_xg, away_xg, 
                home_goals, away_goals,
                (home_goals + away_goals) > 2.5 as over_2_5
            FROM matches
            WHERE home_xg IS NOT NULL
        """
        
        try:
            df = pd.read_sql(query, conn)
            # Engineer basic features for now (since advanced ones like fragility aren't in this view yet)
            # In a real run, we'd join with player_stats, but let's train a MVP model 
            # based on xG trends (rolling averages would be computed here)
            
            # For this MVP v1, we will construct synthetic features from the raw match rows
            # to mimic the structure needed for the XGBoost model
            df['xG_sum'] = df['home_xg'] + df['away_xg']
            df['fragility_sum_top1xG'] = 0.0 # Placeholder
            df['buildup_ratio'] = 0.5 # Placeholder
            df['structural_balance'] = 1.0 # Placeholder
            df['shots_sum'] = df['xG_sum'] * 10 # Rough proxy
            df['chain_sum'] = 0.0
            df['buildup_sum'] = 0.0
            df['balance_xG_abs'] = abs(df['home_xg'] - df['away_xg'])
            
            print(f"✓ Loaded {len(df)} matches from DB")
            return df
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def train(self, df):
        """Train XGBoost and Logistic Regression models."""
        X = df[self.features]
        # Ensure target is integer (0/1) for XGBoost
        y = df[self.target].astype(int)
        
        print(f"Target distribution:\n{y.value_counts()}")
        if y.nunique() < 2:
            print("❌ Error: Target has only 1 class. improving data quality or skipping.")
            return df.iloc[0:0], df.iloc[0:0][self.target] # Return empty

        # Time-based split (Train on older, Test on newer)
        # Assuming df is sorted by date
        split_idx = int(len(df) * 0.8)
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        print(f"🤖 Training XGBoost on {len(X_train)} matches...")
        self.model_xgb = xgb.XGBClassifier(
            max_depth=3,
            learning_rate=0.05,
            n_estimators=300,
            objective='binary:logistic',
            eval_metric='logloss'
        )
        self.model_xgb.fit(X_train, y_train)

        print(f"📈 Training Logistic Regression (Baseline)...")
        self.model_lr = LogisticRegression(solver='liblinear')
        self.model_lr.fit(X_train, y_train)
        
        # Calibration
        self.model_xgb_calib = CalibratedClassifierCV(self.model_xgb, method='isotonic', cv=3)
        self.model_xgb_calib.fit(X_train, y_train)

        return X_test, y_test

    def evaluate(self, X_test, y_test):
        """Evaluate models with AUC and Brier Score."""
        preds_xgb = self.model_xgb_calib.predict_proba(X_test)[:, 1]
        preds_lr = self.model_lr.predict_proba(X_test)[:, 1]

        auc_xgb = roc_auc_score(y_test, preds_xgb)
        brier_xgb = brier_score_loss(y_test, preds_xgb)
        
        auc_lr = roc_auc_score(y_test, preds_lr)

        print("\n📊 Model Evaluation:")
        print("=" * 60)
        print(f"XGBoost AUC: {auc_xgb:.4f} (Brier: {brier_xgb:.4f})")
        print(f"LogReg AUC:  {auc_lr:.4f}")
        
        return preds_xgb

    def save_model(self, path='soccer_model_v1.pkl'):
        """Save the best model to disk."""
        with open(path, 'wb') as f:
            pickle.dump(self.model_xgb_calib, f)
        print(f"✅ Model saved to {path}")

if __name__ == "__main__":
    trainer = SoccerModelTrainer()
    
    # Load data
    df = trainer.load_data()
    
    if not df.empty:
        # Train
        X_test, y_test = trainer.train(df)
        
        # Evaluate
        trainer.evaluate(X_test, y_test)
        
        # Save
        trainer.save_model()
    else:
        print("❌ No data found to train on.")
