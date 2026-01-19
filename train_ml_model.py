#!/usr/bin/env python3
"""
Train ML Model

Standalone script to train the machine learning model on historical data.
"""

import sys
from ml_models import train_and_save_model
from utils import log

def main():
    """Train and save ML model."""
    print("\n" + "="*60)
    print("🤖 TRAINING ML MODEL")
    print("="*60 + "\n")

    # Train model on last 90 days of data
    log("TRAIN", "Starting ML model training...")

    model = train_and_save_model(sport=None, days_back=90)

    if model.is_trained:
        print("\n✅ Model training complete!")
        print(f"\nPerformance Metrics:")
        for name, metrics in model.performance_metrics.items():
            print(f"\n{name.upper()}:")
            print(f"  Accuracy: {metrics['accuracy']:.2%}")
            print(f"  AUC: {metrics['auc']:.4f}")
            print(f"  Log Loss: {metrics['log_loss']:.4f}")
    else:
        print("\n❌ Model training failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
