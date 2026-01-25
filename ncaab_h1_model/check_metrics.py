import pickle
import json
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from ncaab_h1_train import H1_ModelTrainer

def check_metrics():
    print("📊 Evaluating Model Accuracy...")
    
    # Load Trainer & Data (Paths relative to inside ncaab_h1_model/)
    trainer = H1_ModelTrainer(games_path='data/historical_games.json')
    X, y, metadata = trainer.prepare_training_data()
    
    # Load Trained Model
    with open('models/h1_total_model.pkl', 'rb') as f:
        model = pickle.load(f)
        
    # Predict
    preds = model.predict(X)
    
    # Calculate Metrics
    mae = mean_absolute_error(y, preds)
    rmse = np.sqrt(mean_squared_error(y, preds))
    
    print(f"\n📈 Overall Performance (All {len(y)} Games):")
    print(f"MAE: {mae:.2f} points")
    print(f"RMSE: {rmse:.2f} points")
    
    # Baseline (Avg of teams)
    # Feature 0 is home_h1_avg, Feature 1 is away_h1_avg
    # This is a naive baseline: (Home Avg + Away Avg) / 2? Or just Sum?
    # In the trainer we used: baseline_preds = X_test[:, 0] + X_test[:, 1]
    # Wait, features 0 and 1 are raw averages? Let's check ncaab_h1_train.py features.
    # feature_vector = [features['home_h1_avg'], features['away_h1_avg']...]
    # H1 totals are usually Home + Away, so Sum is the baseline.
    
    baseline_preds = X[:, 0] + X[:, 1]
    baseline_mae = mean_absolute_error(y, baseline_preds)
    
    print(f"\n📉 Baseline Performance (Raw Averages):")
    print(f"MAE: {baseline_mae:.2f} points")
    
    improvement = ((baseline_mae - mae) / baseline_mae) * 100
    print(f"\n✅ Model Improvement over Baseline: {improvement:.1f}%")

if __name__ == "__main__":
    check_metrics()
