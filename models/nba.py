import pandas as pd
import numpy as np
import joblib
import json
import os
from datetime import datetime
from db.connection import get_db

MODEL_PATH_ML = "models/nba_model_ml_v2.joblib"
MODEL_PATH_TOT = "models/nba_model_total_v2.joblib"
MODEL_REGISTRY = "models/registry.json"
MODEL_PATH_ML = "models/nba_model_ml_v2.joblib" # Fallback
MODEL_PATH_TOT = "models/nba_model_total_v2.joblib"
# FEATURES_PATH = "models/nba_features_v2.json"
# RESIDUALS_PATH = "models/nba_total_residuals.json"

class NBAModel:
    def __init__(self):
        self.model = None
        self.model_tot = None
        self.features = []
        self.residuals = {}
        self.registry = {}
        self.load_registry()
        self.load_model()
        
    def load_registry(self):
        try:
            if os.path.exists(MODEL_REGISTRY):
                with open(MODEL_REGISTRY, 'r') as f:
                    self.registry = json.load(f)
                print(f"✅ Loaded Model Registry: {MODEL_REGISTRY}")
            else:
                print("⚠️ No Registry Init found.")
        except Exception as e:
            print(f"❌ Registry Load Error: {e}")

    def load_model(self):
        # Resolve Paths from Registry or Fallback
        path_ml = self.registry.get('nba_ml', {}).get('active_path', MODEL_PATH_ML)
        path_tot = self.registry.get('nba_total', {}).get('active_path', MODEL_PATH_TOT)
        path_feat = self.registry.get('features', {}).get('path', "models/nba_features_v2.json")
        path_resid = self.registry.get('nba_total', {}).get('sigma_path', "models/nba_total_residuals.json")
        
        if os.path.exists(path_ml):
            self.model = joblib.load(path_ml)
            print(f"✅ Loaded NBA ML Model: {path_ml}")
        else:
            print(f"❌ NBA Model not found: {path_ml}")
            
        if os.path.exists(path_feat):
            with open(path_feat, 'r') as f:
                self.features = json.load(f)
        else:
            print(f"❌ NBA Features not found: {path_feat}")

        if os.path.exists(path_tot):
            self.model_tot = joblib.load(path_tot)
            print(f"✅ Loaded NBA Totals Model: {path_tot}")
            
        if os.path.exists(path_resid):
            with open(path_resid, 'r') as f:
                self.residuals = json.load(f)
                # Ensure they are sorted (should be from JSON, but safety first)
                for k in self.residuals:
                    self.residuals[k] = sorted(self.residuals[k])
                print(f"✅ Loaded Residuals Distribution for {list(self.residuals.keys())}")
        else:
             print(f"❌ Residuals not found: {path_resid}")

    def predict_match(self, game_id, home_team, away_team, game_date, current_odds):
        """
        Generate prediction for a live game.
        Requires constructing the feature vector from DB history.
        """
        if not self.model: return None
        
        # 1. Fetch/Construct Features
        # We need the rolling stats for Home and Away entering this game.
        # This implies we have essentially run build_nba_features logic up to PREVIOUS game.
        # We can query the LAST row for Home and Away from `nba_model_traing` and shift?
        # Better: Re-use the logic from build_nba_features but targeted.
        
        feat_row = self._build_live_features(home_team, away_team, game_date, current_odds)
        if feat_row is None:
            return None
            
        # 2a. Predict ML
        try:
            X = feat_row[self.features] # Features is list of names
        except KeyError as e:
            print(f"⚠️ Missing features for {home_team} vs {away_team}: {e}")
            return None
            
        prob_home = self.model.predict_proba(X)[0][1]
        
        # 2b. Predict Total
        prob_over = 0.5
        expected_total = 0.0
        
        if self.model_tot and 'total_line' in current_odds:
            line = float(current_odds['total_line'])
            
            # Add line to features if needed (Regression trained with line)
            # The X vector likely needs 'total_line' if feature selection included it.
            # Our training script ADDS 'total_line' to features if not present.
            # But 'self.features' loaded from JSON usually captures the Training features.
            # If train script saved 'features_v2.json' WITHOUT 'total_line' but used it in X...
            # Wait, `t_train_t[features_reg]` where `features_reg = features + ['total_line']`.
            # So 'features_v2.json' might NOT encompass 'total_line'.
            # We must be careful.
            # The safest bet is constructing X_tot explicitly.
            
            X_tot = X.copy()
            X_tot['total_line'] = line
            
            # Predict Residual (Actual - Line)
            pred_resid = self.model_tot.predict(X_tot)[0]
            expected_total = line + pred_resid
            
            # Bucket Selection
            bucket = 'Med'
            if line < 227: bucket = 'Low' 
            elif line > 233: bucket = 'High'
            
            # Empirical Prob Calculation
            # P(Over) = P(Resid > Line - Pred)
            diff = line - expected_total
            
            r_list = self.residuals.get(bucket, self.residuals.get('Global', []))
            if r_list:
                import bisect
                # bisect_right returns insertion point after elements <= diff
                # Elements > diff are from idx to end
                idx = bisect.bisect_right(r_list, diff)
                prob_over = (len(r_list) - idx) / len(r_list)
                
                # Calibration Clip (Optional, strictly empirical is safer)
                prob_over = max(0.01, min(0.99, prob_over))
            else:
                prob_over = 0.5 # Fallback
            
            # print(f"DEBUG TOT: Line={line}, Exp={expected_total:.2f}, Bucket={bucket}, P(Over)={prob_over:.3f}")

        return {
            'prob_home': prob_home,
            'prob_away': 1 - prob_home,
            'prob_over': float(prob_over),
            'expected_total': float(expected_total),
            'features': feat_row.to_dict(orient='records')[0]
        }

    def _get_abbr(self, name):
        # Mapping Full -> Abbr
        mapping = {
            'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN', 'Charlotte Hornets': 'CHA',
            'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE', 'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN',
            'Detroit Pistons': 'DET', 'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
            'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM', 'Miami Heat': 'MIA',
            'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN', 'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK',
            'Oklahoma City Thunder': 'OKC', 'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
            'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS', 'Toronto Raptors': 'TOR',
            'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
        }
        return mapping.get(name, name) # specific overrides
        
    def _build_live_features(self, home_team, away_team, game_date, odds):
        # Normalize to Abbr
        h_abbr = self._get_abbr(home_team)
        a_abbr = self._get_abbr(away_team)
        
        # This is the tricky part: feature engineering on the fly.
        # We need:
        # - Rolling Stats (EFG, TOV, etc.)
        # - Schedule Stats (Rest, B2B)
        # - Matchup Stats (Reb Mismatch)
        # - Market Stats (Implied Prob)
        
        # FASTEST PATH: 
        # Query `nba_model_train` for the most recent game of Home and Away to get their "Season" and "Rolling" stats?
        # No, rolling stats are attached to the *game*.
        # We need to calculate the rolling stats *after* the last game.
        
        # Query: Retrieve last 10 games for HomeTeam and AwayTeam from DB `nba_historical_games`.
        # Calculate Rolling locally.
        
        conn = get_db()
        try:
            # Fetch last 15 games for both teams
            # We need to map team names to IDs or use names if consistent.
            # Assuming team names match DB (fuzzy match risk).
            
            # Helper to get team ID
            qt = "SELECT team_id FROM nba_teams WHERE team_name = %s" # Assuming table exists?
            # Actually build_nba_features uses `nba_historical_games` which has names.
            
            # Let's just pull raw games for the names.
            # UPDATED: Use Abbreviations for query
            q_hist = """
                SELECT * FROM nba_historical_games 
                WHERE (home_team_name = %s OR away_team_name = %s)
                AND game_date < %s
                ORDER BY game_date DESC LIMIT 20
            """
            
            # We need 2 queries (one for home, one for away) to be clean
            df_h = pd.read_sql(q_hist, conn, params=(h_abbr, h_abbr, game_date))
            df_a = pd.read_sql(q_hist, conn, params=(a_abbr, a_abbr, game_date))
            
            if len(df_h) < 3 or len(df_a) < 3:
                # Not enough history
                print(f"⚠️ Not enough history for {h_abbr} ({len(df_h)}) or {a_abbr} ({len(df_a)})")
                return None
                
            # CALC ROLLING (Simplify for Pilot: Just take avg of last N)
            # Function to calculate stats from a set of games
            def get_stats(df, team_name, role='Home'):
                # Normalize perspective
                stats = []
                for _, g in df.iterrows():
                    is_h = g['home_team_name'] == team_name
                    stats.append({
                        'date': g['game_date'],
                        'efg': g['home_efg_pct'] if is_h else g['away_efg_pct'],
                        'tov': g['home_tov_pct'] if is_h else g['away_tov_pct'],
                        'orb': g['home_orb_pct'] if is_h else g['away_orb_pct'],
                        'pace': g['pace'],
                        'opp_orb': g['away_orb_pct'] if is_h else g['home_orb_pct'],
                        
                        # Added for Feature Parity
                        'points': g['home_score'] if is_h else g['away_score'],
                        'opp_points': g['away_score'] if is_h else g['home_score'],
                        'opp_efg': g['away_efg_pct'] if is_h else g['home_efg_pct'],
                        'opp_tov': g['away_tov_pct'] if is_h else g['home_tov_pct'],
                        
                        # Phase 3: 3PAr (Calculated if missing)
                        '3par': g.get('home_3par', g.get('home_fg3a', 0) / g.get('home_fga', 1) if g.get('home_fga', 0) > 0 else 0) if is_h else g.get('away_3par', g.get('away_fg3a', 0) / g.get('away_fga', 1) if g.get('away_fga', 0) > 0 else 0),
                        'opp_3par': g.get('away_3par', g.get('away_fg3a', 0) / g.get('away_fga', 1) if g.get('away_fga', 0) > 0 else 0) if is_h else g.get('home_3par', g.get('home_fg3a', 0) / g.get('home_fga', 1) if g.get('home_fga', 0) > 0 else 0)
                    })
                sdf = pd.DataFrame(stats).sort_values('date')
                sdf['date'] = pd.to_datetime(sdf['date'])
                
                # Rollings
                # We need specific windows: 3, 5, 10
                res = {}
                for w in [3, 5, 10]:
                    last_w = sdf.tail(w)
                    res[f'roll_{w}_efg'] = last_w['efg'].mean()
                    res[f'roll_{w}_tov'] = last_w['tov'].mean()
                    res[f'roll_{w}_orb'] = last_w['orb'].mean()
                    res[f'roll_{w}_pace'] = last_w['pace'].mean()
                    res[f'roll_{w}_opp_orb'] = last_w['opp_orb'].mean() 
                    
                    # Added
                    res[f'roll_{w}_points'] = last_w['points'].mean()
                    res[f'roll_{w}_opp_points'] = last_w['opp_points'].mean()
                    res[f'roll_{w}_opp_efg'] = last_w['opp_efg'].mean()
                    res[f'roll_{w}_opp_tov'] = last_w['opp_tov'].mean()
                    res[f'roll_{w}_3par'] = last_w['3par'].mean()
                    res[f'roll_{w}_opp_3par'] = last_w['opp_3par'].mean()
                
                # Season Ops
                res['sea_efg'] = sdf['efg'].mean()
                res['sea_tov'] = sdf['tov'].mean()
                res['sea_orb'] = sdf['orb'].mean()
                res['sea_pace'] = sdf['pace'].mean()
                res['sea_opp_orb'] = sdf['opp_orb'].mean()
                
                # Added Sea
                res['sea_points'] = sdf['points'].mean()
                res['sea_opp_points'] = sdf['opp_points'].mean()
                res['sea_opp_efg'] = sdf['opp_efg'].mean()
                res['sea_opp_tov'] = sdf['opp_tov'].mean()
                res['sea_3par'] = sdf['3par'].mean()
                res['sea_opp_3par'] = sdf['opp_3par'].mean()
                
                # Rest / B2B
                last_date = pd.to_datetime(sdf['date'].max())
                gd = pd.to_datetime(game_date)
                
                if pd.notna(last_date):
                    print(f"DEBUG TZ: last_date={last_date} ({last_date.tzinfo}) | gd={gd} ({gd.tzinfo})")
                    # Diff
                    if gd.tzinfo is not None:
                        gd = gd.tz_localize(None)
                    if last_date.tzinfo is not None:
                        last_date = last_date.tz_localize(None)
                        
                    days = (gd - last_date).days

                    res['rest_days'] = days
                    res['is_b2b'] = 1 if days == 1 else 0
                    
                    # Games in 5/7
                    # Count games in window
                    window_start_5 = gd - pd.Timedelta(days=5)
                    window_start_7 = gd - pd.Timedelta(days=7)
                    res['games_in_5'] = len(sdf[sdf['date'] > window_start_5]) + 1 # Include today? No, entering.
                    res['games_in_7'] = len(sdf[sdf['date'] > window_start_7]) + 1
                else:
                    res['rest_days'] = 3
                    res['is_b2b'] = 0
                    res['games_in_5'] = 2
                    res['games_in_7'] = 3
                
                return res

            s_h = get_stats(df_h, h_abbr)
            s_a = get_stats(df_a, a_abbr)
            
            # Combine into Feature Row
            # Prefix h_ and a_
            final = {}
            for k, v in s_h.items(): final[f'h_{k}'] = v
            for k, v in s_a.items(): final[f'a_{k}'] = v
            
            # Context
            final['h_is_home'] = 1
            final['a_is_home'] = 0
            
            # Market (Implied)
            final['ml_home'] = odds.get('home_odds', 2.0)
            final['ml_away'] = odds.get('away_odds', 2.0)
            final['implied_prob_home'] = 1 / final['ml_home']
            final['implied_prob_away'] = 1 / final['ml_away']
            
            # Matchups (Phase 6)
            final['reb_mismatch'] = final['h_sea_orb'] + final['a_sea_opp_orb']
            final['threept_mismatch'] = final['h_sea_3par'] + final['a_sea_opp_3par']
            
            # Create DF and Coerce Numeric (Crucial for XGBoost object error)
            df_final = pd.DataFrame([final])
            df_final = df_final.apply(pd.to_numeric, errors='ignore')
            
            return df_final
            
        except Exception as e:
            print(f"❌ Feature Build Error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            conn.close()

if __name__ == "__main__":
    # Test Driver
    model = NBAModel()
    print("🧠 Testing Feature Build...")
    # Use real team names from DB
    res = model.predict_match(
        "test_1", "Philadelphia 76ers", "Boston Celtics", "2025-02-01", 
        {'home_odds': 1.9, 'away_odds': 1.9}
    )
    if res:
        print(f"✅ Prediction: {res}")
    else:
        print("❌ No Prediction generated.")
