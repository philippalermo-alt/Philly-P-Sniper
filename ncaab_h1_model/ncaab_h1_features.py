"""
NCAAB H1 Feature Engineering
Transforms raw team profiles into predictive features.
"""

import json
import numpy as np
from typing import Dict, List
import os
import sys

# Add parent and current directory to path
curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(curr_dir) # For sibling imports (team_name_mapper)
sys.path.append(os.path.dirname(curr_dir)) # For parent imports (data_sources)

try:
    from ncaab_kenpom import KenPomClient
except ImportError:
    # Fallback if running from different context
    try:
        from data_sources.ncaab_kenpom import KenPomClient
    except ImportError:
        KenPomClient = None

from team_name_mapper import normalize_team_name

class H1_FeatureEngine:
    def __init__(self, profiles_path=None):
        """Load team H1/H2 profiles and KenPom data."""
        if profiles_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            profiles_path = os.path.join(base_dir, 'data', 'team_h1_profiles.json')

        with open(profiles_path, 'r') as f:
            self.profiles = json.load(f)

        # Load KenPom tempo data (cached)
        self.kenpom_data = {}
        if KenPomClient:
            try:
                kp_client = KenPomClient()
                df = kp_client.get_efficiency_stats()
                if not df.empty:
                    # Convert to dict for fast lookup
                    for _, row in df.iterrows():
                        self.kenpom_data[row['Team']] = {
                            'tempo': row['AdjT'],
                            'adj_em': row['AdjEM'],
                            'adj_o': row['AdjO'],
                            'adj_d': row['AdjD']
                        }
                    print(f"✓ Loaded KenPom data for {len(self.kenpom_data)} teams")
            except Exception as e:
                print(f"⚠️ Could not load KenPom data: {e}")
                print("   Continuing without tempo features...")

    def get_team_features(self, team_name: str, is_home: bool) -> Dict:
        """Get H1-specific features for a team."""
        # Normalize team name to match dataset
        normalized_name = normalize_team_name(team_name)

        if normalized_name not in self.profiles:
            # ROBUST MATCHING STRATEGY (Centralized)
            from utils.team_names import robust_match_team
            
            found_profile = None
            
            # Use high threshold (0.85) and token constraints
            matched_name = robust_match_team(normalized_name, self.profiles.keys(), threshold=0.85)
            
            if matched_name:
                print(f"   ✨ [ROBUST MATCH] '{normalized_name}' -> '{matched_name}'")
                found_profile = self.profiles[matched_name]
            else:
                 # Fallback: Try raw name one last time?
                 # Often normalization strips something vital?
                 # Try matching raw team_name against profiles
                 matched_name_raw = robust_match_team(team_name, self.profiles.keys(), threshold=0.85)
                 if matched_name_raw:
                      print(f"   ✨ [ROBUST MATCH RAW] '{team_name}' -> '{matched_name_raw}'")
                      found_profile = self.profiles[matched_name_raw]

            if found_profile:
                profile = found_profile
            else:
                print(f"[MISSING PROFILE] raw='{team_name}' normalized='{normalized_name}'")
                return self._get_default_features(is_home)
        else:
            profile = self.profiles[normalized_name]

        # Home court adjustment (teams typically score 2-3 more points at home in H1)
        home_boost = 2.5 if is_home else 0.0

        # Get KenPom stats (if available)
        kp_stats = self._get_kenpom_stats(team_name)

        features = {
            'h1_avg_score': profile['h1_avg_score'] + home_boost,
            'h1_ratio': profile['h1_ratio'],
            'h1_std': profile['h1_std'],
            'h2_ratio': profile['h2_ratio'],
            'consistency': profile['consistency_score'],
            'games_played': min(profile['games_played'], 30),
            'tempo': kp_stats.get('tempo', 68.0),
            'adj_o': kp_stats.get('adj_o', 105.0), # Default to ~avg efficiency
            'adj_d': kp_stats.get('adj_d', 105.0)
        }

        return features

    def _get_kenpom_stats(self, team_name: str) -> Dict:
        """Get KenPom stats (Tempo, AdjO, AdjD) for a team."""
        # Try exact match first
        if team_name in self.kenpom_data:
            return self.kenpom_data[team_name]

        # Try fuzzy match
        import difflib
        kp_teams = list(self.kenpom_data.keys())
        matches = difflib.get_close_matches(team_name, kp_teams, n=1, cutoff=0.7)

        if matches:
            return self.kenpom_data[matches[0]]

        # Default values
        return {'tempo': 68.0, 'adj_o': 105.0, 'adj_d': 105.0}

    def _get_default_features(self, is_home: bool) -> Dict:
        """Return league average features for unknown teams."""
        home_boost = 2.5 if is_home else 0.0

        return {
            'h1_avg_score': 32.0 + home_boost,
            'h1_ratio': 0.48,
            'h1_std': 7.5,
            'h2_ratio': 0.52,
            'consistency': 50.0,
            'games_played': 10,
            'tempo': 68.0,
            'adj_o': 105.0,
            'adj_d': 105.0
        }

    def build_match_features(self, home_team: str, away_team: str) -> Dict:
        """
        Build complete feature vector for an upcoming match.
        """
        home_feat = self.get_team_features(home_team, is_home=True)
        away_feat = self.get_team_features(away_team, is_home=False)

        # Base prediction: sum of team H1 averages
        expected_h1_total = home_feat['h1_avg_score'] + away_feat['h1_avg_score']

        # Ratio-based features
        avg_h1_ratio = (home_feat['h1_ratio'] + away_feat['h1_ratio']) / 2
        h1_ratio_diff = abs(home_feat['h1_ratio'] - away_feat['h1_ratio'])

        # Variance features
        combined_std = np.sqrt(home_feat['h1_std']**2 + away_feat['h1_std']**2)

        # Consistency features
        avg_consistency = (home_feat['consistency'] + away_feat['consistency']) / 2
        consistency_diff = abs(home_feat['consistency'] - away_feat['consistency'])

        # Experience weighting
        min_games = min(home_feat['games_played'], away_feat['games_played'])
        experience_weight = min(min_games / 20, 1.0)

        # Tempo features
        home_tempo = home_feat['tempo']
        away_tempo = away_feat['tempo']
        avg_tempo = (home_tempo + away_tempo) / 2
        tempo_diff = abs(home_tempo - away_tempo)

        # Pace Interaction (New)
        pace_multiplier = avg_tempo / 68.0
        pace_adjusted_total = expected_h1_total * pace_multiplier

        # Efficiency Features (New)
        home_adj_o = home_feat['adj_o']
        home_adj_d = home_feat['adj_d']
        away_adj_o = away_feat['adj_o']
        away_adj_d = away_feat['adj_d']

        # Mismatches (Offense vs Defense)
        # Positive = Offense Advantage, Negative = Defense Advantage
        home_o_adv = home_adj_o - away_adj_d
        away_o_adv = away_adj_o - home_adj_d
        avg_efficiency_mismatch = (home_o_adv + away_o_adv) / 2

        features = {
            # Core predictions
            'expected_h1_total': round(expected_h1_total, 2),
            'pace_adjusted_total': round(pace_adjusted_total, 2), # NEW

            # Team-specific
            'home_h1_avg': home_feat['h1_avg_score'],
            'away_h1_avg': away_feat['h1_avg_score'],
            'home_h1_ratio': home_feat['h1_ratio'],
            'away_h1_ratio': away_feat['h1_ratio'],
            'home_h1_std': home_feat['h1_std'],
            'away_h1_std': away_feat['h1_std'],
            'home_consistency': home_feat['consistency'],
            'away_consistency': away_feat['consistency'],
            'home_tempo': round(home_tempo, 1),
            'away_tempo': round(away_tempo, 1),

            # NEW Efficiency Features
            'home_adj_o': round(home_adj_o, 1),
            'home_adj_d': round(home_adj_d, 1),
            'away_adj_o': round(away_adj_o, 1),
            'away_adj_d': round(away_adj_d, 1),

            # Matchup features
            'avg_h1_ratio': round(avg_h1_ratio, 3),
            'h1_ratio_diff': round(h1_ratio_diff, 3),
            'combined_std': round(combined_std, 2),
            'avg_consistency': round(avg_consistency, 2),
            'consistency_diff': round(consistency_diff, 2),
            'avg_tempo': round(avg_tempo, 1),
            'tempo_diff': round(tempo_diff, 1),
            'pace_multiplier': round(pace_multiplier, 3),
            'experience_weight': round(experience_weight, 3),
            'avg_efficiency_mismatch': round(avg_efficiency_mismatch, 2), # NEW

            # Metadata
            'home_team': home_team,
            'away_team': away_team,
            'min_games_played': min_games
        }

        return features

    def get_confidence_score(self, features: Dict) -> float:
        """
        Calculate prediction confidence (0-100).
        Higher = more reliable prediction based on data quality.

        Confidence is based on:
        1. Sample size (games played)
        2. Team consistency (lower variance = more predictable)
        3. H1 ratio stability (teams with extreme H1 splits may be less reliable)
        """
        min_games = features['min_games_played']

        # 1. Sample Size Score (0-50 points)
        # Need 20+ games for full confidence, penalize heavily below 10
        if min_games < 10:
            games_score = min_games * 2  # 0-20 points for <10 games
        elif min_games < 20:
            games_score = 20 + (min_games - 10)  # 20-30 points for 10-20 games
        else:
            games_score = 30 + min((min_games - 20) / 10 * 20, 20)  # 30-50 points for 20+ games

        # 2. Consistency Score (0-30 points)
        # Lower combined std = more predictable outcomes
        # Typical std range: 5-12 points
        # Score: 30 at std=5, 15 at std=8.5, 0 at std=12+
        combined_std = features['combined_std']
        if combined_std <= 5:
            consistency_score = 30
        elif combined_std >= 12:
            consistency_score = 0
        else:
            # Linear interpolation between 5 and 12
            consistency_score = 30 * (12 - combined_std) / 7

        # 3. Reliability Score (0-20 points)
        # Teams with consistent H1 patterns are more predictable
        # Penalize extreme H1 ratios (>0.52 or <0.44) as they may not persist
        avg_h1_ratio = features['avg_h1_ratio']
        avg_consistency = features['avg_consistency']

        if 0.46 <= avg_h1_ratio <= 0.50:  # Most reliable zone
            ratio_score = 10
        elif 0.44 <= avg_h1_ratio <= 0.52:  # Still good
            ratio_score = 7
        else:  # Extreme splits - less reliable
            ratio_score = 3

        # Add team consistency metric
        if avg_consistency >= 85:
            team_consistency_score = 10
        elif avg_consistency >= 75:
            team_consistency_score = 7
        else:
            team_consistency_score = max(0, (avg_consistency - 50) / 25 * 7)

        reliability_score = ratio_score + team_consistency_score

        # Total confidence (max 100)
        total = games_score + consistency_score + reliability_score

        return round(min(total, 100), 1)

if __name__ == "__main__":
    # Example usage
    engine = H1_FeatureEngine()

    # Test matchup
    features = engine.build_match_features("Duke", "North Carolina")
    confidence = engine.get_confidence_score(features)

    print("EXAMPLE MATCHUP: Duke vs North Carolina")
    print("=" * 60)
    print(f"Expected H1 Total: {features['expected_h1_total']}")
    print(f"Home (Duke) H1 Avg: {features['home_h1_avg']:.1f}")
    print(f"Away (UNC) H1 Avg: {features['away_h1_avg']:.1f}")
    print(f"Avg H1 Ratio: {features['avg_h1_ratio']:.1%}")
    print(f"Combined Std Dev: {features['combined_std']:.1f}")
    print(f"Confidence Score: {confidence}/100")
