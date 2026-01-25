"""
NCAAB H1 Live Prediction
Predicts first half totals for upcoming games.
"""

import pickle
import numpy as np
from ncaab_h1_features import H1_FeatureEngine

class H1_Predictor:
    def __init__(self, model_path=None):
        """Load trained model."""
        import os
        if model_path is None:
            # Default to relative to this file
            base_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(base_dir, 'models', 'h1_total_model.pkl')
            
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)

        self.feature_engine = H1_FeatureEngine()

    def predict(self, home_team: str, away_team: str, verbose=True):
        """
        Predict H1 total for a matchup.

        Returns:
            dict with prediction, confidence, breakdown, and matchup-specific std
        """
        # Get features
        features = self.feature_engine.build_match_features(home_team, away_team)
        confidence = self.feature_engine.get_confidence_score(features)

        # Build feature vector (same order as training)
        # UPDATED: Added 4 new tempo features (19 total, up from 15)
        X = np.array([[
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
        ]])

        # Predict RESIDUAL (Actual - Pace_Adjusted_Total)
        predicted_residual = self.model.predict(X)[0]
        
        # Final Prediction = Baseline + Residual
        baseline = features['pace_adjusted_total']
        predicted_total = baseline + predicted_residual

        # Use matchup-specific std (not hardcoded 7.5)
        # combined_std accounts for both teams' variance
        expected_std = features['combined_std']

        result = {
            'home_team': home_team,
            'away_team': away_team,
            'predicted_h1_total': round(predicted_total, 1),
            'confidence': confidence,
            'expected_std': round(expected_std, 1),
            'home_h1_avg': round(features['home_h1_avg'], 1),
            'away_h1_avg': round(features['away_h1_avg'], 1),
            'breakdown': features
        }

        if verbose:
            self._print_prediction(result)

        return result

    def _print_prediction(self, result):
        """Pretty print prediction."""
        print("\n" + "=" * 70)
        print(f"🏀 FIRST HALF PREDICTION: {result['home_team']} vs {result['away_team']}")
        print("=" * 70)
        print(f"\n📊 Predicted H1 Total: {result['predicted_h1_total']}")
        print(f"   Confidence: {result['confidence']}/100")
        print(f"   Expected Std Dev: {result['expected_std']}")
        print(f"\n   {result['home_team']} H1 Avg: {result['home_h1_avg']}")
        print(f"   {result['away_team']} H1 Avg: {result['away_h1_avg']}")

    def calculate_edge(self, predicted_total, sportsbook_line, over_odds, under_odds, expected_std=None):
        """
        Calculate edge vs sportsbook H1 total line.

        Args:
            predicted_total: Model's predicted H1 total
            sportsbook_line: Book's H1 total line
            over_odds: American odds for Over
            under_odds: American odds for Under
            expected_std: Matchup-specific standard deviation (if None, uses 7.5 default)

        Returns:
            dict with edge analysis
        """
        from scipy.stats import norm

        # Convert odds to decimal
        def american_to_decimal(odds):
            if odds > 0:
                return 1 + (odds / 100)
            else:
                return 1 + (100 / abs(odds))

        over_decimal = american_to_decimal(over_odds)
        under_decimal = american_to_decimal(under_odds)

        # Calculate implied probabilities
        over_implied = 1 / over_decimal
        under_implied = 1 / under_decimal

        # Model's true probabilities (using normal distribution)
        # Use matchup-specific std if provided, otherwise default to 7.5
        # FIX: Regress std to mean (0.6 * combined + 0.4 * 7.5) to avoid fake EV on volatile games
        raw_std = expected_std if expected_std is not None else 7.5
        h1_std = (0.6 * raw_std) + (0.4 * 7.5)
        
        # SAFETY: Enforce minimum floor. College kids are inconsistent. 
        # Std < 6.5 implies dangerously low variance for a 35-point half.
        h1_std = max(6.5, h1_std)

        model_prob_over = 1 - norm.cdf(sportsbook_line, predicted_total, h1_std)
        model_prob_under = norm.cdf(sportsbook_line, predicted_total, h1_std)

        # Calculate edges
        over_edge = model_prob_over - over_implied
        under_edge = model_prob_under - under_implied

        # Expected value
        over_ev = (model_prob_over * (over_decimal - 1)) - ((1 - model_prob_over) * 1)
        under_ev = (model_prob_under * (under_decimal - 1)) - ((1 - model_prob_under) * 1)

        return {
            'sportsbook_line': sportsbook_line,
            'model_prediction': predicted_total,
            'difference': round(predicted_total - sportsbook_line, 1),

            'over': {
                'odds': over_odds,
                'implied_prob': round(over_implied, 3),
                'model_prob': round(model_prob_over, 3),
                'edge': round(over_edge, 3),
                'ev': round(over_ev, 3),
                'recommendation': 'BET' if over_edge > 0.05 else 'PASS'
            },

            'under': {
                'odds': under_odds,
                'implied_prob': round(under_implied, 3),
                'model_prob': round(model_prob_under, 3),
                'edge': round(under_edge, 3),
                'ev': round(under_ev, 3),
                'recommendation': 'BET' if under_edge > 0.05 else 'PASS'
            }
        }

if __name__ == "__main__":
    # Example usage
    predictor = H1_Predictor()

    # Predict
    result = predictor.predict("Duke", "North Carolina")

    # Check edge vs sportsbook line
    # Example: Book has H1 total 68.5, Over -110, Under -110
    edge_analysis = predictor.calculate_edge(
        predicted_total=result['predicted_h1_total'],
        sportsbook_line=68.5,
        over_odds=-110,
        under_odds=-110
    )

    print("\n" + "=" * 70)
    print("💰 EDGE ANALYSIS")
    print("=" * 70)
    print(f"\nSportsbook Line: {edge_analysis['sportsbook_line']}")
    print(f"Model Prediction: {edge_analysis['model_prediction']}")
    print(f"Difference: {edge_analysis['difference']:+.1f}")

    print(f"\n🔼 OVER {edge_analysis['sportsbook_line']}:")
    print(f"   Odds: {edge_analysis['over']['odds']}")
    print(f"   Implied Prob: {edge_analysis['over']['implied_prob']:.1%}")
    print(f"   Model Prob: {edge_analysis['over']['model_prob']:.1%}")
    print(f"   Edge: {edge_analysis['over']['edge']:+.1%}")
    print(f"   Expected Value: {edge_analysis['over']['ev']:+.2%}")
    print(f"   👉 {edge_analysis['over']['recommendation']}")

    print(f"\n🔽 UNDER {edge_analysis['sportsbook_line']}:")
    print(f"   Odds: {edge_analysis['under']['odds']}")
    print(f"   Implied Prob: {edge_analysis['under']['implied_prob']:.1%}")
    print(f"   Model Prob: {edge_analysis['under']['model_prob']:.1%}")
    print(f"   Edge: {edge_analysis['under']['edge']:+.1%}")
    print(f"   Expected Value: {edge_analysis['under']['ev']:+.2%}")
    print(f"   👉 {edge_analysis['under']['recommendation']}")
