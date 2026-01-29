
import sys
import os
import numpy as np
from scipy import stats
import json

# Add root to path
sys.path.append(os.getcwd())
# Add H1 Model dir to path for internal module resolution
sys.path.append(os.path.join(os.getcwd(), 'ncaab_h1_model'))

from ncaab_h1_model.ncaab_h1_train import H1_ModelTrainer

def check_normality():
    print("📉 Verifying Residual Distribution (Assumption: Gaussian)...")
    
    # 1. Get Model & Data
    trainer = H1_ModelTrainer()
    # Ensure fresh training/prep
    X, y, metadata = trainer.prepare_training_data()
    
    # Check if we should retrain or use existing model?
    # Since we harden the pipeline, let's retrain to be sure we match current code.
    print("   Training fresh model to get residuals...")
    model, metrics = trainer.train()
    
    # 2. Extract Test Residuals (Out of Sample)
    # Temporal Split 80/20
    split_idx = int(len(y) * 0.8)
    y_test_residuals = y[split_idx:]
    
    # 3. Stats
    mean_resid = np.mean(y_test_residuals)
    std_resid = np.std(y_test_residuals)
    
    print(f"\n📊 Residual Stats (Test Set, N={len(y_test_residuals)}):")
    print(f"   Mean: {mean_resid:.4f} (Ideal: 0)")
    print(f"   Std:  {std_resid:.4f}")
    
    # 4. Kolmogorov-Smirnov Test
    # Null Hypothesis: Sample comes from Normal Distribution(mean, std)
    # We standardize the residuals first: (x - mean) / std -> compares to Standard Normal
    z_scores = (y_test_residuals - mean_resid) / std_resid
    
    ks_statistic, p_value = stats.kstest(z_scores, 'norm')
    
    print(f"\n🧪 KS Test Results:")
    print(f"   Statistic: {ks_statistic:.4f}")
    print(f"   P-Value:   {p_value:.6f}")
    
    alpha = 0.05
    if p_value < alpha:
        print(f"❌ FAIL: P-value ({p_value:.6f}) < {alpha}. Distribution is NOT Normal.")
        print("   -> Recommendation: Switch to Quantile Regression or Poisson (Phase 3.3).")
    else:
        print(f"✅ PASS: P-value ({p_value:.6f}) >= {alpha}. Cannot reject Normal assumption.")
        print("   -> Gaussian assumption matches reality.")

    # 5. Simple Text Histogram
    print("\n   Histogram:")
    counts, bins = np.histogram(y_test_residuals, bins=10)
    max_count = max(counts)
    for count, bin_edge in zip(counts, bins):
        bar = '#' * int(40 * count / max_count)
        print(f"   {bin_edge:6.1f} | {bar} ({count})")

if __name__ == "__main__":
    check_normality()
