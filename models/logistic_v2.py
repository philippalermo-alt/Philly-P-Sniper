import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss
import joblib
import os
from database import get_db

class LogisticModelV2:
    """
    Phase 2 Model: Logistic Regression.
    Weights standard proprietary features dynamically based on historical performance.
    
    Formula: P(Win) ~ ImpliedProb + MyProb + SharpMoney% + TimeToKickoff + xG_Diff + DvP_Rank
    """
    
    def __init__(self, model_path='models/v2_logistic.pkl'):
        self.model_path = model_path
        self.model = None
        self.features = [
            'implied_prob', 
            'true_prob',      # My Poisson/Base model prob
            'ticket_pct',     # Proxy for Sharp Money / Public Sentiment
            'minutes_to_kickoff',
            'xg_diff',        # (Home xG - Away xG) avg last 5 games
            'dvp_rank'        # Defense vs Position Rank
        ]
        
    def load_data(self):
        """
        Load training data from intelligence_log.
        """
        conn = get_db()
        if not conn:
            print("❌ DB Connection failed. Cannot load training data.")
            return pd.DataFrame()
            
        query = """
        SELECT 
            odds, true_prob, ticket_pct, 
            EXTRACT(EPOCH FROM (kickoff - timestamp))/60 as minutes_to_kickoff,
            home_xg, away_xg, dvp_rank,
            outcome
        FROM intelligence_log
        WHERE outcome IN ('WON', 'LOST')
        """
        try:
            df = pd.read_sql(query, conn)
            # Feature Engineering
            df['implied_prob'] = 1 / df['odds']
            df['xg_diff'] = df['home_xg'] - df['away_xg']
            
            # Fill NaNs check
            df = df.fillna(0) # Simple imputation for now
            
            # Target
            df['target'] = df['outcome'].apply(lambda x: 1 if x == 'WON' else 0)
            
            return df
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return pd.DataFrame()

    def train(self):
        """
        Train the model and save it.
        """
        df = self.load_data()
        if df.empty or len(df) < 50:
            print("⚠️ Not enough data to train model (<50 samples).")
            return

        X = df[self.features]
        y = df['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = LogisticRegression(class_weight='balanced')
        self.model.fit(X_train, y_train)
        
        # Evaluate
        preds = self.model.predict(X_test)
        probs = self.model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, preds)
        loss = log_loss(y_test, probs)
        
        print(f"✅ Model V2 Trained.")
        print(f"   Accuracy: {acc:.2f}")
        print(f"   Log Loss: {loss:.4f}")
        print(f"   Coefficients: {dict(zip(self.features, self.model.coef_[0]))}")
        
        # Save
        joblib.dump(self.model, self.model_path)
        print(f"💾 Model saved to {self.model_path}")

    def predict(self, input_data):
        """
        Predict probability for a new bet.
        input_data: dict containing feature values.
        """
        if not self.model:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
            else:
                print("⚠️ Model not trained yet.")
                return 0.5

        # Create DataFrame for single row
        # Ensure all features exist, default to 0
        row = {k: input_data.get(k, 0) for k in self.features}
        X = pd.DataFrame([row])
        
        prob = self.model.predict_proba(X)[0][1]
        return prob

if __name__ == "__main__":
    # Test Run
    model = LogisticModelV2()
    print("Attempting to train model...")
    model.train()
