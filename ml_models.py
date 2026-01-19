"""
Machine Learning Model Training and Prediction

Trains and manages ML models to improve betting predictions.
"""

import numpy as np
import pickle
import os
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss, classification_report

from ml_features import prepare_training_data
from utils import log

class BettingMLModel:
    """
    Machine Learning model for betting predictions.

    Combines multiple models (ensemble) to predict bet outcomes.
    """

    def __init__(self, model_type='ensemble'):
        """
        Initialize ML model.

        Args:
            model_type: 'random_forest', 'gradient_boosting', 'logistic', or 'ensemble'
        """
        self.model_type = model_type
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_names = None
        self.is_trained = False
        self.performance_metrics = {}

    def train(self, start_date=None, end_date=None, sport=None):
        """
        Train the ML model on historical data.

        Args:
            start_date: Start date for training data
            end_date: End date for training data
            sport: Filter by sport (optional)

        Returns:
            dict: Training performance metrics
        """
        log("ML", f"Training {self.model_type} model...")

        # Prepare training data
        X, y, feature_names = prepare_training_data(start_date, end_date, sport)

        if X is None or len(X) == 0:
            log("ERROR", "No training data available")
            return {}

        self.feature_names = feature_names

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        log("ML", f"Training on {len(X_train)} samples, testing on {len(X_test)} samples")

        # Train models
        if self.model_type == 'ensemble' or self.model_type == 'random_forest':
            log("ML", "Training Random Forest...")
            rf = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42,
                n_jobs=-1
            )
            rf.fit(X_train_scaled, y_train)
            self.models['random_forest'] = rf

        if self.model_type == 'ensemble' or self.model_type == 'gradient_boosting':
            log("ML", "Training Gradient Boosting...")
            gb = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                min_samples_split=20,
                min_samples_leaf=10,
                random_state=42
            )
            gb.fit(X_train_scaled, y_train)
            self.models['gradient_boosting'] = gb

        if self.model_type == 'ensemble' or self.model_type == 'logistic':
            log("ML", "Training Logistic Regression...")
            lr = LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=42
            )
            lr.fit(X_train_scaled, y_train)
            self.models['logistic'] = lr

        # Evaluate models
        self.performance_metrics = self._evaluate_models(X_test_scaled, y_test)

        # Print feature importance (for tree-based models)
        if 'random_forest' in self.models:
            self._print_feature_importance(self.models['random_forest'])

        self.is_trained = True

        log("ML", "Training complete!")

        return self.performance_metrics

    def _evaluate_models(self, X_test, y_test):
        """Evaluate model performance on test set."""
        metrics = {}

        for name, model in self.models.items():
            y_pred = model.predict(X_test)
            y_pred_proba = model.predict_proba(X_test)[:, 1]

            accuracy = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(y_test, y_pred_proba)
            logloss = log_loss(y_test, y_pred_proba)

            metrics[name] = {
                'accuracy': round(accuracy, 4),
                'auc': round(auc, 4),
                'log_loss': round(logloss, 4)
            }

            log("ML", f"{name}: Accuracy={accuracy:.4f}, AUC={auc:.4f}, LogLoss={logloss:.4f}")

        # Ensemble prediction
        if len(self.models) > 1:
            ensemble_proba = np.mean([m.predict_proba(X_test)[:, 1] for m in self.models.values()], axis=0)
            ensemble_pred = (ensemble_proba > 0.5).astype(int)

            accuracy = accuracy_score(y_test, ensemble_pred)
            auc = roc_auc_score(y_test, ensemble_proba)
            logloss = log_loss(y_test, ensemble_proba)

            metrics['ensemble'] = {
                'accuracy': round(accuracy, 4),
                'auc': round(auc, 4),
                'log_loss': round(logloss, 4)
            }

            log("ML", f"Ensemble: Accuracy={accuracy:.4f}, AUC={auc:.4f}, LogLoss={logloss:.4f}")

        return metrics

    def _print_feature_importance(self, model):
        """Print feature importance for tree-based models."""
        if not hasattr(model, 'feature_importances_'):
            return

        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]

        log("ML", "\nTop 10 Feature Importances:")
        for i in range(min(10, len(indices))):
            idx = indices[i]
            log("ML", f"  {i+1}. {self.feature_names[idx]}: {importances[idx]:.4f}")

    def predict_proba(self, features):
        """
        Predict win probability for a bet.

        Args:
            features: Dictionary or array of features

        Returns:
            float: Predicted win probability
        """
        if not self.is_trained:
            log("WARNING", "Model not trained, returning default probability")
            return None

        # Convert dict to array if needed
        if isinstance(features, dict):
            feature_array = np.array([[features[name] for name in self.feature_names]])
        else:
            feature_array = np.array([features])

        # Scale features
        feature_array_scaled = self.scaler.transform(feature_array)

        # Get predictions from all models
        if len(self.models) == 1:
            model = list(self.models.values())[0]
            return model.predict_proba(feature_array_scaled)[0, 1]
        else:
            # Ensemble average
            probas = [m.predict_proba(feature_array_scaled)[0, 1] for m in self.models.values()]
            return np.mean(probas)

    def save(self, filepath='models/betting_model.pkl'):
        """Save model to disk."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        model_data = {
            'model_type': self.model_type,
            'models': self.models,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'is_trained': self.is_trained,
            'performance_metrics': self.performance_metrics,
            'trained_at': datetime.now()
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        log("ML", f"Model saved to {filepath}")

    @classmethod
    def load(cls, filepath='models/betting_model.pkl'):
        """Load model from disk."""
        if not os.path.exists(filepath):
            log("WARNING", f"Model file not found: {filepath}")
            return None

        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        model = cls(model_type=model_data['model_type'])
        model.models = model_data['models']
        model.scaler = model_data['scaler']
        model.feature_names = model_data['feature_names']
        model.is_trained = model_data['is_trained']
        model.performance_metrics = model_data.get('performance_metrics', {})

        log("ML", f"Model loaded from {filepath} (trained at {model_data.get('trained_at')})")

        return model

    def cross_validate(self, X, y, cv=5):
        """
        Perform cross-validation.

        Args:
            X: Feature matrix
            y: Labels
            cv: Number of folds

        Returns:
            dict: Cross-validation scores
        """
        results = {}

        X_scaled = self.scaler.fit_transform(X)

        for name, model in self.models.items():
            scores = cross_val_score(model, X_scaled, y, cv=cv, scoring='roc_auc')
            results[name] = {
                'mean_auc': round(scores.mean(), 4),
                'std_auc': round(scores.std(), 4),
                'scores': scores.tolist()
            }
            log("ML", f"{name} CV: {scores.mean():.4f} (+/- {scores.std():.4f})")

        return results

def train_and_save_model(sport=None, days_back=90):
    """
    Convenience function to train and save a model.

    Args:
        sport: Filter by sport (optional)
        days_back: Number of days of historical data to use

    Returns:
        BettingMLModel: Trained model
    """
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    model = BettingMLModel(model_type='ensemble')
    metrics = model.train(start_date=start_date, end_date=end_date, sport=sport)

    if model.is_trained:
        model.save()
        log("ML", f"Model training complete. Performance: {metrics}")
    else:
        log("ERROR", "Model training failed")

    return model

def load_or_train_model(filepath='models/betting_model.pkl', retrain_if_old_days=7):
    """
    Load existing model or train a new one if needed.

    Args:
        filepath: Path to model file
        retrain_if_old_days: Retrain if model is older than this many days

    Returns:
        BettingMLModel: Loaded or trained model
    """
    # Try to load existing model
    model = BettingMLModel.load(filepath)

    if model is None:
        log("ML", "No existing model found, training new model...")
        return train_and_save_model()

    # Check if model is too old
    if os.path.exists(filepath):
        file_age_days = (datetime.now().timestamp() - os.path.getmtime(filepath)) / 86400

        if file_age_days > retrain_if_old_days:
            log("ML", f"Model is {file_age_days:.1f} days old, retraining...")
            return train_and_save_model()

    return model
