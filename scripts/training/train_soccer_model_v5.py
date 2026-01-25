"""
Soccer Model Trainer V5 (Occam's Razor)
---------------------------------------
Sanity check proved 'exp_total_xg' predicts Over 2.5 with AUC ~0.60.
XGBoost overfitted (AUC 0.55).
This script uses plain Logistic Regression to calibrate the strong signal from exp_total_xg.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, classification_report
from sklearn.calibration import CalibratedClassifierCV
import pickle
from database import get_db

# Reuse V4 Feature Engineering Logic exactly
from train_soccer_model_v4 import SoccerModelTrainerV4

class SoccerModelTrainerV5(SoccerModelTrainerV4):
    def __init__(self):
        super().__init__()
        # Simplified Feature Set
        self.features = [
            'exp_total_xg',   # The King Feature
            'league_avg_xg',  # Context
            'xg_imbalance'    # V5.1 Add: Imbalance
        ]
        
    def train(self, df):
        print(f"🤖 Training V5 (LogReg) on {len(df)} matches...")
        
        # Engineer "V5.1" features on the fly
        # xg_imbalance = abs(exp_h - exp_a)
        # We can reconstruct exp_h/exp_a from the V4 columns
        exp_h = (df['home_att_h'] + df['away_def_a']) / 2
        exp_a = (df['away_att_a'] + df['home_def_h']) / 2
        df['xg_imbalance'] = abs(exp_h - exp_a)

        split = int(len(df) * 0.8)
        train_df = df.iloc[:split]
        test_df = df.iloc[split:]
        
        X_train = train_df[self.features]
        y_train = train_df[self.target]
        X_test = test_df[self.features]
        y_test = test_df[self.target]
        
        X_train = train_df[self.features]
        self.model = LogisticRegression(solver='liblinear')
        self.model.fit(X_train, y_train)
        
        # Calibration (Sigmoid - proven best for this dataset)
        self.model_calib = CalibratedClassifierCV(self.model, method='sigmoid', cv=3)
        self.model_calib.fit(X_train, y_train)
        
        # Eval & Threshold Optimization
        preds_proba = self.model_calib.predict_proba(X_test)[:, 1]
        
        # Find Optimal Threshold (Maximize Balanced Accuracy)
        from sklearn.metrics import balanced_accuracy_score
        
        best_thresh = 0.50
        best_score = 0.0
        
        thresholds = np.arange(0.40, 0.60, 0.01)
        for t in thresholds:
            p_class = (preds_proba > t).astype(int)
            bal_acc = balanced_accuracy_score(y_test, p_class)
            if bal_acc > best_score:
                best_score = bal_acc
                best_thresh = t
                
        preds_class = (preds_proba > best_thresh).astype(int)
        
        auc = roc_auc_score(y_test, preds_proba)
        brier = brier_score_loss(y_test, preds_proba)
        
        print("\n" + "="*50)
        print(f"📊 V5.2 FINAL RESULTS (Sigmoid + Thresh {best_thresh:.2f})")
        print("="*50)
        print(f"AUC Score:   {auc:.4f}")
        print(f"Brier Score: {brier:.4f}")
        print(f"Best Thresh: {best_thresh:.2f} (Balanced Acc: {best_score:.4f})")
        print("-" * 30)
        print(classification_report(y_test, preds_class))
        
        # Coefficients (Interpretation)
        # Note: CalibratedClassifierCV wraps the base model
        print("-" * 30)
        print("Coefficients:")
        for name, coef in zip(self.features, self.model.coef_[0]):
            print(f"{name}: {coef:.4f}")
        print("="*50)
        
        # Save
        with open('soccer_model_v5.pkl', 'wb') as f:
            pickle.dump(self.model_calib, f)
        print("\n✅ Saved soccer_model_v5.pkl")

if __name__ == "__main__":
    t = SoccerModelTrainerV5()
    df = t.load_and_engineer()
    if not df.empty:
        t.train(df)
