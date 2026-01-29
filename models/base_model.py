import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import joblib
import os
from db.connection import get_db

class BaseModel:
    """
    Base class for sport-specific logistic regression models.
    """
    def __init__(self, sport_name, features, model_path):
        self.sport_name = sport_name
        self.features = features
        self.model_path = model_path
        self.model = None

    def load_data(self):
        conn = get_db()
        if not conn:
            print("❌ DB Connection failed.")
            return pd.DataFrame()

        # Base query - child classes can override or we select all and filter
        # Selecting all potential columns. Columns that don't apply will be 0 or ignored
        query = """
        SELECT 
            sport, odds, true_prob, ticket_pct, 
            EXTRACT(EPOCH FROM (kickoff - timestamp))/60 as minutes_to_kickoff,
            kickoff,
            home_xg, away_xg, dvp_rank, 
            home_adj_em, away_adj_em,
            home_adj_o, away_adj_o,
            home_adj_d, away_adj_d,
            home_tempo, away_tempo,
            outcome
        FROM intelligence_log
        WHERE outcome IN ('WON', 'LOST')
        """
        try:
            df = pd.read_sql(query, conn)
            
            # Filter by sport
            # Flexible matching: 'basketball_nba' contains 'nba'
            df = df[df['sport'].str.contains(self.sport_name, case=False, na=False)]
            
            if df.empty:
                return df

            # Common Feature Engineering
            df['implied_prob'] = 1 / df['odds']
            df['target'] = df['outcome'].apply(lambda x: 1 if x == 'WON' else 0)
            df = df.fillna(0)
            return df
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return pd.DataFrame()

    def train(self):
        df = self.load_data()
        if df.empty or len(df) < 20: # Lower threshold for individual sports
            print(f"⚠️ Not enough data to train {self.sport_name} model (<20 samples).")
            return

        # Feature Engineering specific to the rows (handled in load_data or here)
        # We assume child classes might add computed columns if needed, but for now
        # we strictly use the columns defined in self.features
        
        # Check if features exist in DF
        missing_cols = [c for c in self.features if c not in df.columns]
        if missing_cols:
            print(f"❌ Missing columns for {self.sport_name}: {missing_cols}")
            return

        X = df[self.features]
        y = df['target']
        
        try:
            # --- TEMPORAL SPLIT (Audit Fix 1.1) ---
            # Sort by kickoff date to ensure we train on past, predict on future
            if 'kickoff' in df.columns:
                df = df.sort_values('kickoff').reset_index(drop=True)
                X = df[self.features]
                y = df['target']
                
                # Manual 80/20 Split
                split_idx = int(len(df) * 0.8)
                X_train = X.iloc[:split_idx]
                X_test = X.iloc[split_idx:]
                y_train = y.iloc[:split_idx]
                y_test = y.iloc[split_idx:]
                
                # Check timestamps for leakage
                train_max = df.iloc[split_idx-1]['kickoff']
                test_min = df.iloc[split_idx]['kickoff']
                
                if train_max > test_min:
                     # This should not happen if sorted, but verifying logic
                     print(f"⚠️ Warning: Timestamp Overlap. Train Max: {train_max}, Test Min: {test_min}")
                else:
                     print(f"✅ Temporal Split Verified: Train End {train_max} < Test Start {test_min}")
            else:
                print("⚠️ Kickoff column missing for Temporal Split. Falling back to Random (Risk of Leakage).")
                from sklearn.model_selection import train_test_split
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            self.model = LogisticRegression(class_weight='balanced')
            self.model.fit(X_train, y_train)
            
            preds = self.model.predict(X_test)
            acc = accuracy_score(y_test, preds)
            
            print(f"✅ {self.sport_name.upper()} Model Trained. Acc: {acc:.2f}")
            print(f"   Coeffs: {dict(zip(self.features, self.model.coef_[0]))}")
            
            joblib.dump(self.model, self.model_path)
        except Exception as e:
            print(f"❌ Training failed for {self.sport_name}: {e}")

    def predict(self, input_data):
        if not self.model:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                return input_data.get('true_prob', 0.5)

        row = {k: input_data.get(k, 0) for k in self.features}
        X = pd.DataFrame([row])
        return self.model.predict_proba(X)[0][1]
