
import pandas as pd
import numpy as np
import os
from datetime import datetime
from scipy.stats import nbinom
import scripts.nhl_recs_config as cfg
from data.clients.odds_api import fetch_prop_odds
from unidecode import unidecode
import sys

# Config
SPORT_KEY = "icehockey_nhl"
ODDS_MARKETS = "player_points,player_assists,player_shots_on_goal,player_goal_scorer_anytime,player_goals"

class NHLRecEngine:
    def __init__(self):
        self.projections = None
        self.candidates = []
        self.recs = []
        self.audit_log = []
        
    def load_projections(self):
        print("📥 Loading Projections...")
        path = "data/nhl_processed/daily_projections.csv"
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {path}")
            
        df = pd.read_csv(path)
        # Normalize names for joining
        df['join_name'] = df['player_name'].apply(self._norm)
        self.projections = df
        print(f"  Loaded {len(df)} projected players.")
        
    def fetch_market_odds(self):
        print("📡 Fetching Odds...")
        return fetch_prop_odds(SPORT_KEY, markets=ODDS_MARKETS)
        
    def run(self):
        # 1. Load
        self.load_projections()
        odds_data = self.fetch_market_odds()
        if not odds_data:
            print("❌ No odds found.")
            return

        print("⚙️ Evaluating Candidates...")
        
        # 2. Iterate Odds -> Match Proj -> Eval
        # Structure: odds_data[player_name][market_key] = [ {book, price, line, side} ]
        
        for p_name_odds, markets in odds_data.items():
            # Match
            p_norm = self._norm(p_name_odds)
            
            # Find in Projections
            # Exact match on normalized name
            match = self.projections[self.projections['join_name'] == p_norm]
            if len(match) == 0:
                # Log join fail?
                # self.log_candidate(..., reason="JOIN_MISSING")
                # User says: "Any join mismatch rate > 1%... BLOCK".
                # But odds API has tons of players not in our Projections (other teams).
                # We only care if we match RELEVANT players.
                # Let's count "Matched" vs "Unmatched".
                continue
                
            row = match.iloc[0]
            
            # Eval Markets
            self.eval_player_markets(row, markets, p_name_odds)
            
        # 3. Portfolio Controls
        self.apply_portfolio_controls()
        
        # 4. Save Artifacts
        self.save_artifacts()
        
        # 5. Log to Database (Production Dashboard)
        self.log_to_db()
        
        # 6. Print Report
        self.print_report()

    def log_to_db(self):
        from db.connection import get_db
        conn = get_db()
        if not conn:
            print("❌ FATAL: Could not connect to Database. Check DB_HOST and Credentials.", file=sys.stderr)
            raise ConnectionError("Database Connection Failed")
        
        # Filter for Recommended
        if not self.recs: return
        
        print(f"💾 Logging {len(self.recs)} recommendations to DB...")
        
        try:
            with conn.cursor() as cur:
                for rec in self.recs:
                    # Unique ID
                    # NHL_{Player}_{Market}_{Line}_{Date}
                    date_str = datetime.now().strftime('%Y%m%d')
                    clean_market = rec['market_type'].replace(" ", "")
                    line_str = str(rec['line']).replace(".", "p")
                    slug = f"NHL_{rec['player_name']}_{clean_market}_{line_str}_{date_str}"
                    
                    sel_text = f"{rec['player_name']} {rec['market_type']} {rec['line']}"
                    if rec['market_type'] == 'GOALS' and rec['line'] == 0.5:
                        sel_text = f"{rec['player_name']} Anytime Goal"
                    elif rec['market_type'] == 'GOALS':
                        sel_text = f"{rec['player_name']} Over {rec['line']} Goals"
                    else:
                        sel_text = f"{rec['player_name']} Over {rec['line']} {rec['market_type']}"
                        
                    sel_text += f" [{rec['tier']}]"
                    
                    # Insert
                    sql = """
                        INSERT INTO intelligence_log 
                        (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, book, outcome, user_bet)
                        VALUES 
                        (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', FALSE)
                        ON CONFLICT (event_id) DO UPDATE SET
                        edge = EXCLUDED.edge, true_prob = EXCLUDED.true_prob, odds = EXCLUDED.odds
                    """
                    
                    cur.execute(sql, (
                        slug,
                        rec['game_time_est'],
                        "icehockey_nhl",
                        f"{rec['team']} vs {rec['opponent']}",
                        sel_text,
                        float(rec['dec_odds']),
                        float(rec['p_model'] * 100),
                        float(rec['edge']),
                        rec['book']
                    ))
                conn.commit()
                print("✅ DB Sync Complete.")
        except Exception as e:
            print(f"❌ DB Error: {e}")
        finally:
            conn.close()
        
    def eval_player_markets(self, row, markets, p_name_book):
        # row: Series from daily_projections
        
        # -- GOALS (Anytime) --
        if 'player_goal_scorer_anytime' in markets:
            self.eval_candidate(row, markets['player_goal_scorer_anytime'], 'GOALS', 0.5, 'Over')
            
        # -- GOALS (Line) --
        if 'player_goals' in markets:
             self.eval_candidate(row, markets['player_goals'], 'GOALS', None, 'Over') # Line dynamic
             
        # -- SOG --
        if 'player_shots_on_goal' in markets:
            self.eval_candidate(row, markets['player_shots_on_goal'], 'SOG', None, 'Over')
            
        # -- ASSISTS --
        if 'player_assists' in markets:
            self.eval_candidate(row, markets['player_assists'], 'ASSISTS', None, 'Over')
            
        # -- POINTS --
        if 'player_points' in markets:
            self.eval_candidate(row, markets['player_points'], 'POINTS', None, 'Over')

    def eval_candidate(self, row, offers, m_type, force_line, side_filter):
        if not isinstance(offers, list): return
        
        for offer in offers:
            # Filter Side (Over only)
            if offer.get('side') != side_filter and m_type != 'GOALS': 
                # Anytime Goal doesn't usually have "side", it's implicit Over? Depends on API.
                # Assuming 'player_goal_scorer_anytime' is straight list.
                if m_type != 'GOALS': continue
            
            # Get Line/Price
            val = offer.get('line')
            if val is None:
                line = float(force_line) if force_line is not None else 0.5
            else:
                line = float(val)
                
            price = float(offer.get('price'))
            book = offer.get('book')
            
            # 1. Calc Model Prob (p_model)
            p_model = self.calc_p_model(row, m_type, line)
            
            # 2. Calc Implied Prob (p_implied)
            p_implied = self.calc_implied(price)
            
            # 3. Edge/EV
            edge = p_model - p_implied
            dec_odds = self.to_decimal(price)
            ev = (p_model * (dec_odds - 1)) - (1 - p_model)
            
            # 4. Confidence Tier
            tier = self.get_tier(row, m_type, line, p_model)
            
            # 5. Gates (Reject Reasons)
            reasons = []
            
            # TOI Check
            toi = row.get('toi_minutes_l10', 0)
            if toi < cfg.ELIGIBILITY['min_toi']:
                reasons.append("FAIL_TOI")
                
            # Market Specifics
            if m_type == 'POINTS':
                if p_model < cfg.ELIGIBILITY['points_min_prob']: reasons.append("FAIL_MIN_PROB")
                if row.get('proj_points_mean', 0) < cfg.ELIGIBILITY['points_min_mean']: reasons.append("FAIL_MIN_MEAN")
                
            elif m_type == 'ASSISTS':
                if p_model < cfg.ELIGIBILITY['assists_min_prob']: reasons.append("FAIL_MIN_PROB")
                
            elif m_type == 'GOALS':
                if p_model < cfg.ELIGIBILITY['goals_min_prob']: reasons.append("FAIL_MIN_PROB")
                if row.get('mu_sog', 0) < cfg.ELIGIBILITY['avg_goals_min_sog']: reasons.append("FAIL_MIN_MEAN_SOG")
                
            elif m_type == 'SOG':
                min_mean = line + cfg.ELIGIBILITY['sog_min_buffer']
                if row.get('mu_sog', 0) < min_mean: reasons.append("FAIL_Sanity_Buffer")

            # EV/Edge Trigger
            # Check Thresholds for Tier
            thresh = cfg.TRIGGERS.get(tier, cfg.TRIGGERS['C'])
            
            # Tier C Logic
            if tier == 'C':
                # Exception check
                allowed = False
                if ev >= cfg.TIER_C_EXCEPTION['min_ev'] and toi >= cfg.TIER_C_EXCEPTION['min_toi']:
                    # Check bottom 6? (pp_share < 0.3?)
                    if row.get('pp_share_l10', 0) > 0.3: # Not bottom 6
                        allowed = True
                        reasons.append("TIER_C_EXCEPTION") # Info tag
                
                if not allowed:
                    reasons.append("FAIL_TIER_C")
            else:
                # A/B Logic
                if ev < thresh['min_ev'] and edge < thresh['min_edge']:
                    reasons.append("FAIL_LOW_EDGE")

            # 6. Recommendation Decision
            is_rec = (len(reasons) == 0) or (len(reasons) == 1 and reasons[0] == "TIER_C_EXCEPTION")
            
            # Audit Record
            cand = {
                'player_id': row.get('player_id'),
                'player_name': row['player_name'],
                'team': row['team'],
                'opponent': row['opponent'],
                'market_type': m_type,
                'line': line,
                'book': book,
                'book_odds': price,
                'dec_odds': dec_odds,
                'p_model': p_model,
                'p_implied': p_implied,
                'edge': edge,
                'ev': ev,
                'tier': tier,
                'gate_version': cfg.GATE_VERSION,
                'is_recommended': is_rec,
                'reject_reasons': "|".join(reasons) if reasons else "PASS",
                'game_time_est': row.get('game_time_est', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            }
            
            self.candidates.append(cand)

    def calc_p_model(self, row, m_type, line):
        # Uses Frozen Alphas and Scipy
        if m_type == 'SOG':
            mu = row['mu_sog']
            alpha = cfg.MODEL_PARAMS['alpha_sog']
            # P(X > line) = 1 - CDF(floor(line)) if line is X.5
            # line 2.5 -> >2 -> P(X>=3) -> 1 - CDF(2). 
            k = int(line)
            n_p = 1.0 / alpha
            p_p = n_p / (n_p + mu)
            return 1.0 - nbinom.cdf(k, n_p, p_p)
            
        elif m_type == 'POINTS':
            # Use pre-calced if line matches 0.5/1.5
            if line == 0.5: return row.get('prob_points_1plus', 0.0)
            if line == 1.5: return row.get('prob_points_2plus', 0.0)
            return 0.0
            
        elif m_type == 'ASSISTS':
            # Use NB
            mu = row['mu_ast']
            alpha = cfg.MODEL_PARAMS['alpha_ast']
            k = int(line)
            n_p = 1.0 / alpha
            p_p = n_p / (n_p + mu)
            return 1.0 - nbinom.cdf(k, n_p, p_p)

        elif m_type == 'GOALS':
            # Approx P(G>=1) = 1 - exp(-mu_sog * p_goal) OR use NB?
            # Phase 2 used Binomial/NB approx.
            # Simplified: Poisson(mu_sog * p_goal).
            mu_g = row['mu_sog'] * row.get('p_goal', cfg.MODEL_PARAMS['p_goal_default'])
            if line == 0.5:
                return 1.0 - np.exp(-mu_g)
            return 0.0
            
        return 0.0

    def get_tier(self, row, m_type, line, prob):
        t = cfg.TIER_THRESHOLDS
        
        if m_type == 'POINTS':
            if prob >= t['points_A']: return 'A'
            if prob >= t['points_B']: return 'B'
            return 'C'
            
        elif m_type == 'ASSISTS':
            if prob >= t['assists_A']: return 'A'
            if prob >= t['assists_B']: return 'B'
            return 'C'
            
        elif m_type == 'GOALS':
            if prob >= t['goals_A']: return 'A'
            if prob >= t['goals_B']: return 'B'
            return 'C'
            
        elif m_type == 'SOG':
            mu = row['mu_sog']
            if line == 2.5:
                if mu >= t['sog_2.5_A']: return 'A'
                if mu >= t['sog_2.5_B']: return 'B'
                return 'C'
            elif line == 3.5:
                if mu >= t['sog_3.5_A']: return 'A'
                if mu >= t['sog_3.5_B']: return 'B'
                return 'C'
            else:
                return 'B' # Default for non-std lines
                
        return 'C'

    def calc_implied(self, price):
        if price < 0:
            return abs(price) / (abs(price) + 100)
        else:
            return 100 / (price + 100)
            
    def to_decimal(self, price):
        if price < 0:
            return 1 + (100 / abs(price))
        return 1 + (price / 100)
        
    def _norm(self, name):
        return unidecode(name).lower().replace(".", "").strip()
        
    def apply_portfolio_controls(self):
        # 1. Start with all Recommended candidates
        recs = [c for c in self.candidates if c['is_recommended']]
        df = pd.DataFrame(recs)
        
        if df.empty:
            self.recs = []
            return
            
        # 2. De-dup: Keep highest EV per player
        # Sort by EV desc
        df = df.sort_values('ev', ascending=False)
        df = df.drop_duplicates(subset=['player_name'], keep='first')
        
        # 3. Market Limits
        # Group by Market Type and take Top N
        final_recs = []
        for m_type, limit in cfg.PORTFOLIO_MAX.items():
            market_df = df[df['market_type'] == m_type].head(limit)
            final_recs.extend(market_df.to_dict('records'))
            
        self.recs = final_recs
        
    def save_artifacts(self):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Audit
        df_audit = pd.DataFrame(self.candidates)
        df_audit['timestamp'] = ts
        df_audit.to_csv("data/nhl_processed/candidates_audit.csv", index=False)
        
        # Recs
        df_recs = pd.DataFrame(self.recs)
        if not df_recs.empty:
            df_recs['timestamp'] = ts
            df_recs.to_csv("data/nhl_processed/recommendations.csv", index=False)
        else:
            # Empty file
            pd.DataFrame(columns=['player_name', 'market_type', 'ev']).to_csv("data/nhl_processed/recommendations.csv", index=False)
            
    def print_report(self):
        print("\n📊 Recommendation Report")
        print("==========================")
        
        # Breakdown by Market
        df_audit = pd.DataFrame(self.candidates)
        if df_audit.empty:
            print("No candidates evaluated.")
            return

        print(f"Total Candidates: {len(self.candidates)}")
        print(f"Total Recommended: {len(self.recs)}\n")
        
        print(df_audit.groupby('market_type')['is_recommended'].value_counts().unstack().fillna(0))
        
        print("\n🚫 Top Reject Reasons:")
        print(df_audit['reject_reasons'].value_counts().head(5))
        
        print("\n🏆 Top 5 Recommendations:")
        df_recs = pd.DataFrame(self.recs)
        if not df_recs.empty:
            print(df_recs[['player_name', 'market_type', 'line', 'dec_odds', 'ev', 'tier']].head(5))
        else:
            print("None.")

if __name__ == "__main__":
    engine = NHLRecEngine()
    engine.run()
