"""
Machine Learning Feature Engineering

Creates features for ML models to predict betting outcomes more accurately.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import get_db
from utils import log

def extract_features_for_match(home, away, sport, ratings, market_type, line=None):
    """
    Extract ML features for a single match.

    Args:
        home: Home team name
        away: Away team name
        sport: Sport type
        ratings: Team ratings dictionary
        market_type: 'ml', 'spread', or 'total'
        line: Betting line (for spread/total)

    Returns:
        dict: Feature dictionary
    """
    features = {}

    # Team ratings features
    home_r = ratings.get(home, {})
    away_r = ratings.get(away, {})

    if sport in ['NBA', 'NCAAB']:
        features['home_off_eff'] = home_r.get('offensive_eff', 110.0)
        features['home_def_eff'] = home_r.get('defensive_eff', 110.0)
        features['home_tempo'] = home_r.get('tempo', 70.0)
        features['away_off_eff'] = away_r.get('offensive_eff', 110.0)
        features['away_def_eff'] = away_r.get('defensive_eff', 110.0)
        features['away_tempo'] = away_r.get('tempo', 70.0)

        # Derived features
        features['off_eff_diff'] = features['home_off_eff'] - features['away_off_eff']
        features['def_eff_diff'] = features['away_def_eff'] - features['home_def_eff']
        features['tempo_diff'] = features['home_tempo'] - features['away_tempo']
        features['avg_tempo'] = (features['home_tempo'] + features['away_tempo']) / 2

    elif sport == 'NFL':
        features['home_off_ypp'] = home_r.get('off_ypp', 5.0)
        features['home_def_ypp'] = home_r.get('def_ypp', 5.0)
        features['home_off_ppg'] = home_r.get('off_ppg', 20.0)
        features['home_def_ppg'] = home_r.get('def_ppg', 20.0)
        features['away_off_ypp'] = away_r.get('off_ypp', 5.0)
        features['away_def_ypp'] = away_r.get('def_ypp', 5.0)
        features['away_off_ppg'] = away_r.get('off_ppg', 20.0)
        features['away_def_ppg'] = away_r.get('def_ppg', 20.0)

        # Derived features
        features['ypp_diff'] = (features['home_off_ypp'] - features['home_def_ypp']) - \
                               (features['away_off_ypp'] - features['away_def_ypp'])
        features['ppg_diff'] = (features['home_off_ppg'] - features['home_def_ppg']) - \
                               (features['away_off_ppg'] - features['away_def_ppg'])

    elif sport == 'NHL':
        features['home_attack'] = home_r.get('attack', 1.0)
        features['home_defense'] = home_r.get('defense', 1.0)
        features['away_attack'] = away_r.get('attack', 1.0)
        features['away_defense'] = away_r.get('defense', 1.0)
        features['league_avg_goals'] = home_r.get('league_avg_goals', 3.0)

        # Derived features
        features['attack_diff'] = features['home_attack'] - features['away_attack']
        features['defense_diff'] = features['away_defense'] - features['home_defense']

    # Market-specific features
    features['market_type_ml'] = 1 if market_type == 'ml' else 0
    features['market_type_spread'] = 1 if market_type == 'spread' else 0
    features['market_type_total'] = 1 if market_type == 'total' else 0

    if line is not None:
        features['line'] = line
        features['abs_line'] = abs(line)
    else:
        features['line'] = 0
        features['abs_line'] = 0

    # Sport one-hot encoding
    features['sport_nba'] = 1 if sport == 'NBA' else 0
    features['sport_ncaab'] = 1 if sport == 'NCAAB' else 0
    features['sport_nfl'] = 1 if sport == 'NFL' else 0
    features['sport_nhl'] = 1 if sport == 'NHL' else 0

    # Historical head-to-head features (if available)
    h2h_features = get_head_to_head_features(home, away, sport)
    features.update(h2h_features)

    # Recent form features
    home_form = get_recent_form(home, sport)
    away_form = get_recent_form(away, sport)

    features['home_recent_win_pct'] = home_form.get('win_pct', 0.5)
    features['home_recent_cover_pct'] = home_form.get('cover_pct', 0.5)
    features['away_recent_win_pct'] = away_form.get('win_pct', 0.5)
    features['away_recent_cover_pct'] = away_form.get('cover_pct', 0.5)

    return features

def get_head_to_head_features(home, away, sport, lookback_days=365):
    """Get historical head-to-head matchup features."""
    conn = get_db()
    if not conn:
        return {
            'h2h_games': 0,
            'h2h_home_wins': 0,
            'h2h_avg_total': 0
        }

    try:
        cur = conn.cursor()

        # Look for past matchups
        cur.execute("""
            SELECT teams, outcome, selection
            FROM intelligence_log
            WHERE sport = %s
            AND outcome IN ('WON', 'LOST', 'PUSH')
            AND (teams LIKE %s OR teams LIKE %s)
            AND kickoff > NOW() - INTERVAL '%s days'
        """, (sport, f'%{home}%{away}%', f'%{away}%{home}%', lookback_days))

        rows = cur.fetchall()

        if not rows:
            return {
                'h2h_games': 0,
                'h2h_home_wins': 0,
                'h2h_avg_total': 0
            }

        # Count home wins
        home_wins = sum(1 for r in rows if home in r[0] and r[1] == 'WON')

        return {
            'h2h_games': len(rows),
            'h2h_home_wins': home_wins,
            'h2h_avg_total': 0  # Could calculate if we tracked scores
        }

    except Exception as e:
        log("ERROR", f"Error getting H2H features: {e}")
        return {
            'h2h_games': 0,
            'h2h_home_wins': 0,
            'h2h_avg_total': 0
        }
    finally:
        cur.close()
        conn.close()

def get_recent_form(team, sport, num_games=5):
    """Get recent performance metrics for a team."""
    conn = get_db()
    if not conn:
        return {'win_pct': 0.5, 'cover_pct': 0.5}

    try:
        cur = conn.cursor()

        # Get recent games for this team
        cur.execute("""
            SELECT selection, outcome
            FROM intelligence_log
            WHERE sport = %s
            AND outcome IN ('WON', 'LOST', 'PUSH')
            AND teams LIKE %s
            AND kickoff > NOW() - INTERVAL '30 days'
            ORDER BY kickoff DESC
            LIMIT %s
        """, (sport, f'%{team}%', num_games))

        rows = cur.fetchall()

        if not rows:
            return {'win_pct': 0.5, 'cover_pct': 0.5}

        wins = sum(1 for r in rows if r[1] == 'WON')
        covers = sum(1 for r in rows if r[1] == 'WON')  # Simplified - actual cover logic would check spreads

        return {
            'win_pct': wins / len(rows) if rows else 0.5,
            'cover_pct': covers / len(rows) if rows else 0.5
        }

    except Exception as e:
        log("ERROR", f"Error getting recent form: {e}")
        return {'win_pct': 0.5, 'cover_pct': 0.5}
    finally:
        cur.close()
        conn.close()

def prepare_training_data(start_date=None, end_date=None, sport=None):
    """
    Prepare training dataset from historical bets.

    Args:
        start_date: Start date for training data
        end_date: End date for training data
        sport: Filter by sport (optional)

    Returns:
        tuple: (X, y, feature_names) - features, labels, feature names
    """
    conn = get_db()
    if not conn:
        return None, None, None

    try:
        # Default date range
        if not end_date:
            end_date = datetime.now()
        if not start_date:
            start_date = end_date - timedelta(days=90)

        log("ML", f"Preparing training data from {start_date.date()} to {end_date.date()}")

        cur = conn.cursor()

        # Get settled bets with all relevant data
        query = """
            SELECT
                teams, sport, selection, outcome, odds, edge, true_prob,
                sharp_score, ticket_pct, money_pct, closing_odds
            FROM intelligence_log
            WHERE outcome IN ('WON', 'LOST')
            AND kickoff BETWEEN %s AND %s
        """

        params = [start_date, end_date]

        if sport:
            query += " AND sport = %s"
            params.append(sport)

        cur.execute(query, params)
        rows = cur.fetchall()

        if not rows:
            log("ML", "No training data found")
            return None, None, None

        log("ML", f"Found {len(rows)} training examples")

        # Convert to DataFrame for easier processing
        df = pd.DataFrame(rows, columns=[
            'teams', 'sport', 'selection', 'outcome', 'odds', 'edge',
            'true_prob', 'sharp_score', 'ticket_pct', 'money_pct', 'closing_odds'
        ])

        # Create features
        features_list = []
        labels = []

        for _, row in df.iterrows():
            # Parse teams
            teams_parts = row['teams'].split(' @ ')
            if len(teams_parts) != 2:
                continue

            away, home = teams_parts

            # Determine market type and line
            selection = row['selection']
            if ' ML' in selection:
                market_type = 'ml'
                line = None
            elif 'Over' in selection or 'Under' in selection:
                market_type = 'total'
                try:
                    line = float(selection.split()[-1])
                except:
                    line = None
            else:
                market_type = 'spread'
                try:
                    line = float(selection.split()[-1])
                except:
                    line = None

            # Create feature dict
            features = {
                'odds': row['odds'],
                'edge': row['edge'],
                'true_prob': row['true_prob'],
                'sharp_score': row['sharp_score'] if pd.notna(row['sharp_score']) else 50,
                'ticket_pct': row['ticket_pct'] if pd.notna(row['ticket_pct']) else 50,
                'money_pct': row['money_pct'] if pd.notna(row['money_pct']) else 50,
                'market_type_ml': 1 if market_type == 'ml' else 0,
                'market_type_spread': 1 if market_type == 'spread' else 0,
                'market_type_total': 1 if market_type == 'total' else 0,
                'line': line if line is not None else 0,
                'abs_line': abs(line) if line is not None else 0,
                'sport_nba': 1 if row['sport'] == 'NBA' else 0,
                'sport_ncaab': 1 if row['sport'] == 'NCAAB' else 0,
                'sport_nfl': 1 if row['sport'] == 'NFL' else 0,
                'sport_nhl': 1 if row['sport'] == 'NHL' else 0,
            }

            # Add CLV if available
            if pd.notna(row['closing_odds']) and row['closing_odds'] != row['odds']:
                features['clv'] = ((row['odds'] - row['closing_odds']) / row['odds']) * 100
            else:
                features['clv'] = 0

            # Add sharp indicator
            if pd.notna(row['money_pct']) and pd.notna(row['ticket_pct']):
                features['sharp_indicator'] = row['money_pct'] - row['ticket_pct']
            else:
                features['sharp_indicator'] = 0

            features_list.append(features)
            labels.append(1 if row['outcome'] == 'WON' else 0)

        # Convert to numpy arrays
        feature_names = list(features_list[0].keys())
        X = np.array([[f[name] for name in feature_names] for f in features_list])
        y = np.array(labels)

        log("ML", f"Prepared {len(X)} samples with {len(feature_names)} features")

        return X, y, feature_names

    except Exception as e:
        log("ERROR", f"Error preparing training data: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None
    finally:
        cur.close()
        conn.close()
