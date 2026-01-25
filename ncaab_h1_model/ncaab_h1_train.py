import json
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import pickle
import os

from ncaab_h1_features import H1_FeatureEngine

class H1_ModelTrainer:
    def __init__(self, games_path='data/historical_games.json'):
        """Initialize trainer with historical game data."""
        with open(games_path, 'r') as f:
            self.games = json.load(f)

        self.feature_engine = H1_FeatureEngine()
        self.model = None

    def prepare_training_data(self):
        """Convert historical games into feature matrix + targets."""
        X_list = []
        y_list = []
        metadata_list = []
        
        print("Preparing training data (Target: Residuals)...")

        for game in self.games:
            # Get features for this matchup
            features = self.feature_engine.build_match_features(
                game['home_team'],
                game['away_team']
            )

            # Extract feature vector
            feature_vector = [
                features['home_h1_avg'],
                features['away_h1_avg'],
                features['home_h1_ratio'],
                features['away_h1_ratio'],
                features['home_h1_std'],
                features['away_h1_std'],
                features['home_consistency'],
                features['away_consistency'],
                features['home_tempo'],
                features['away_tempo'],
                features['avg_h1_ratio'],
                features['h1_ratio_diff'],
                features['combined_std'],
                features['avg_consistency'],
                features['consistency_diff'],
                features['avg_tempo'],
                features['tempo_diff'],
                features['pace_multiplier'],
                features['experience_weight'],
                features['pace_adjusted_total'],
                features['home_adj_o'],
                features['home_adj_d'],
                features['away_adj_o'],
                features['away_adj_d'],
                features['avg_efficiency_mismatch']
            ]

            X_list.append(feature_vector)
            
            # MODEL 3.0 TARGET: Train on residuals (Actual - Baseline)
            # Baseline is pace_adjusted_total
            baseline = features['pace_adjusted_total']
            actual = game['h1_total']
            residual = actual - baseline
            
            y_list.append(residual)
            
            metadata_list.append({
                'game_id': game['game_id'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'actual_h1': actual,
                'baseline_h1': baseline,
                'residual': residual
            })

        X = np.array(X_list)
        y = np.array(y_list)

        print(f"✓ Prepared {len(X)} training examples")

        return X, y, metadata_list

    def train(self):
        """Train XGBoost model on residuals."""
        X, y, metadata = self.prepare_training_data()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        print(f"\n🚀 Training XGBoost Model 3.0...")
        
        # XGBoost Configuration (Tuned Option A)
        model = xgb.XGBRegressor(
            n_estimators=1000,
            learning_rate=0.015,
            max_depth=4,           # Increased from 3
            min_child_weight=10,   # Added to reduce noise
            subsample=0.8,         # Explicitly set
            colsample_bytree=0.7,
            reg_alpha=0.5,
            reg_lambda=2.0,
            early_stopping_rounds=50, # Added early stopping
            random_state=42,
            n_jobs=-1
        )

        # Train with early stopping
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )
        
        self.model = model
        
        # Evaluate (Reconstruct Total Predictions)
        # Pred = Baseline + Predicted_Residual
        
        # X matrix columns (hardcoded index for pace_adjusted_total)
        BASELINE_IDX = 19 
        
        train_baseline = X_train[:, BASELINE_IDX]
        test_baseline = X_test[:, BASELINE_IDX]
        
        train_pred_resid = model.predict(X_train)
        test_pred_resid = model.predict(X_test)
        
        train_final_pred = train_baseline + train_pred_resid
        test_final_pred = test_baseline + test_pred_resid
        
        # Actuals
        train_actuals = train_baseline + y_train
        test_actuals = test_baseline + y_test

        train_mae = mean_absolute_error(train_actuals, train_final_pred)
        test_mae = mean_absolute_error(test_actuals, test_final_pred)
        train_rmse = np.sqrt(mean_squared_error(train_actuals, train_final_pred))
        test_rmse = np.sqrt(mean_squared_error(test_actuals, test_final_pred))
        
        # Baseline MAE
        baseline_mae = mean_absolute_error(test_actuals, test_baseline)
        improvement = ((baseline_mae - test_mae) / baseline_mae) * 100
        
        print("\n📊 Model 3.0 Performance (Reconstructed Totals):")
        print("=" * 60)
        print(f"XGB Params: {model.get_params()}")
        print(f"Train MAE:  {train_mae:.2f}")
        print(f"Test MAE:   {test_mae:.2f}")
        print(f"Test RMSE:  {test_rmse:.2f}")
        print(f"Baseline:   {baseline_mae:.2f}")

        return model, {'test_mae': test_mae, 'improvement': improvement}

    def save_model(self, path='models/h1_total_model.pkl'):
        """Save trained model to disk."""
        if self.model is None:
            raise ValueError("No model trained yet. Call train() first.")

        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'wb') as f:
            pickle.dump(self.model, f)

        print(f"\n✅ Model saved to {path}")

if __name__ == "__main__":
    trainer = H1_ModelTrainer()
    trainer.train()
    trainer.save_model()
