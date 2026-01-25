import pandas as pd
import numpy as np
from database import get_db
from utils import log

class PlayerPropsPredictor:
    """
    Predicts player performance props (Shots, Goals, Assists) 
    using historical xG/xA/xGChain data.
    """
    
    def __init__(self, league="EPL", season="2025"):
        self.league = league
        self.season = season
        self.data = self._load_data()
        
    def _load_data(self):
        """Fetch all player stats for the season from DB."""
        conn = get_db()
        if not conn:
            log("ERROR", "DB Connection failed")
            return pd.DataFrame()
        
        query = """
            SELECT player_id, player_name, team_name, team_id, position, minutes, 
                   shots, goals, assists, xg, xa, xg_chain, xg_buildup, match_id
            FROM player_stats
            WHERE league = %s AND season = %s
            ORDER BY match_id ASC
        """
        try:
            log("PROPS", f"DEBUG: Querying league='{self.league}', season='{self.season}'")
            
            # Debug: Check total rows in table
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*), league, season FROM player_stats GROUP BY league, season")
                    stats = cur.fetchall()
                    log("PROPS", f"DEBUG: DB Table Stats: {stats}")
            except:
                pass

            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                df = pd.read_sql(query, conn, params=(self.league, self.season))
            
            log("PROPS", f"Loaded {len(df)} player-match rows for {self.league} {self.season}")
            if len(df) == 0:
                 log("PROPS", "DEBUG: DATAFRAME IS EMPTY! Check table contents vs query params.")

            return df
        except Exception as e:
            log("ERROR", f"Error fetching player data: {e}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_team_defense_ratings(self):
        """
        Calculate xGoals Allowed (xGA) per 90 for every team in the league.
        Returns: dict { 'TeamName': xGA_per_90_float }
        """
        if self.data.empty: return {}

        # 1. Identify Opponents per Match
        # Group by match_id to find the two teams
        match_teams = self.data.groupby('match_id')['team_name'].unique()
        
        # 2. Calculate Total xG Conceded by each team
        team_xga = {} # {Team: Total_xG_Conceded}
        team_mins = {} # {Team: Total_Mins_Played} -> Approx (Matches * 90)

        # Pre-calc xG total per match per team
        # For each match, we sum the xG of Team A to get Team B's xGA
        match_xg = self.data.groupby(['match_id', 'team_name'])['xg'].sum().reset_index()
        
        for mid, teams in match_teams.items():
            if len(teams) != 2: continue # Skip data incomplete matches
            t1, t2 = teams[0], teams[1]
            
            # Get xG created BY t1 (which is xGA for t2)
            t1_xg = match_xg[(match_xg['match_id'] == mid) & (match_xg['team_name'] == t1)]['xg'].sum()
            # Get xG created BY t2 (which is xGA for t1)
            t2_xg = match_xg[(match_xg['match_id'] == mid) & (match_xg['team_name'] == t2)]['xg'].sum()
            
            team_xga[t1] = team_xga.get(t1, 0) + t2_xg
            team_xga[t2] = team_xga.get(t2, 0) + t1_xg
            
            # Count match as 1 game (90 mins)
            team_mins[t1] = team_mins.get(t1, 0) + 90
            team_mins[t2] = team_mins.get(t2, 0) + 90
            
        # 3. Normalize to xGA/90
        ratings = {}
        league_xga_sum = 0
        league_teams = 0
        
        for team, xga in team_xga.items():
            mins = team_mins.get(team, 90)
            if mins == 0: continue
            rating = (xga / mins) * 90
            ratings[team] = rating
            league_xga_sum += rating
            league_teams += 1
            
        self.avg_league_xga = league_xga_sum / max(1, league_teams)
        return ratings

    def get_player_rolling_stats(self, player_name, span=5, upcoming_opponent=None):
        """
        Calculate stats and apply MATCHUP ADJUSTMENT if opponent is provided.
        """
        player_df = self.data[self.data['player_name'] == player_name].copy()
        
        if player_df.empty: return None
        
        # --- ROLLING STATS ---
        player_df['rolling_minutes'] = player_df['minutes'].rolling(window=span, min_periods=1).sum()
        player_df['rolling_shots'] = player_df['shots'].rolling(window=span, min_periods=1).sum()
        player_df['rolling_xg'] = player_df['xg'].rolling(window=span, min_periods=1).sum()
        player_df['rolling_xa'] = player_df['xa'].rolling(window=span, min_periods=1).sum()
        player_df['rolling_xg_chain'] = player_df['xg_chain'].rolling(window=span, min_periods=1).sum()
        
        # Take the most recent row AFTER rolling stats are added
        last_row = player_df.iloc[-1]
        
        if last_row['rolling_minutes'] < 90:
            total_mins = player_df['minutes'].sum()
            if total_mins < 45: return None
            norm_mins = total_mins
            raw_shots = player_df['shots'].sum()
            raw_xg = player_df['xg'].sum()
            raw_xa = player_df['xa'].sum()
            raw_chain = player_df['xg_chain'].sum()
        else:
            norm_mins = last_row['rolling_minutes']
            raw_shots = last_row['rolling_shots']
            raw_xg = last_row['rolling_xg']
            raw_xa = last_row['rolling_xa']
            raw_chain = last_row['rolling_xg_chain']

        # Rate Per 90 (Pace)
        proj_shots_p90 = (raw_shots / norm_mins) * 90
        proj_xg_p90 = (raw_xg / norm_mins) * 90
        proj_xa_p90 = (raw_xa / norm_mins) * 90
        proj_xg_chain_p90 = (raw_chain / norm_mins) * 90

        # --- MATCHUP ADJUSTMENT ---
        matchup_multiplier = 1.0
        defense_rating = "N/A"
        
        if upcoming_opponent and hasattr(self, 'defense_ratings'):
            opp_xga = self.defense_ratings.get(upcoming_opponent, self.avg_league_xga)
            matchup_multiplier = opp_xga / max(0.1, self.avg_league_xga)
            matchup_multiplier = max(0.7, min(1.4, matchup_multiplier))
            defense_rating = f"{opp_xga:.2f} xGA/90"

        # Apply Multiplier to PACE
        final_shots_p90 = proj_shots_p90 * matchup_multiplier
        final_xg_p90 = proj_xg_p90 * matchup_multiplier
        
        # --- EXPECTED MINUTES SCALING ---
        # Calculate expected minutes based on weighted last 5 games
        avg_mins_last_5 = player_df['minutes'].tail(5).mean()
        exp_mins = max(15, avg_mins_last_5) # Floor at 15 to avoid zero-division or log issues

        # Real Game Projection (Volume) = Pace * (Exp Mins / 90)
        proj_shots_game = final_shots_p90 * (exp_mins / 90.0)
        proj_xg_game = final_xg_p90 * (exp_mins / 90.0)

        # --- PROBABILITY (POISSON) ---
        import math
        def poisson_prob_over(lam, line):
            target_k = int(line)
            cumulative_prob = 0.0
            for k in range(target_k + 1):
                cumulative_prob += (math.exp(-lam) * (lam**k)) / math.factorial(k)
            return max(0.0, min(1.0, 1.0 - cumulative_prob))

        # 1. Anytime Goal Probability (Line 0.5) using GAME xG
        prob_goal = poisson_prob_over(proj_xg_game, 0.5) * 100
        
        # 2. 2+ Shots Probability (Line 1.5) using GAME Shots
        prob_2_shots = poisson_prob_over(proj_shots_game, 1.5) * 100
        
        # --- VARIANCE & RELIABILITY ---
        shots_std = player_df['shots'].rolling(window=span, min_periods=1).std().iloc[-1]
        if pd.isna(shots_std): shots_std = 0.0
        
        def get_american_odds(prob_pct):
            if prob_pct <= 0 or prob_pct >= 100: return "+Inf"
            if prob_pct > 50:
                m_line = - (prob_pct / (100 - prob_pct)) * 100
            else:
                m_line = ((100 - prob_pct) / prob_pct) * 100
            return int(round(m_line))

        fair_odds_goal = get_american_odds(prob_goal)
        
        sub_risk = "Low"
        if avg_mins_last_5 < 60: sub_risk = "High"
        elif avg_mins_last_5 < 80: sub_risk = "Med"

        try:
            tid = int(last_row.get('team_id', 0))
        except:
            tid = 0

        return {
            "player_name": player_name,
            "team_name": last_row['team_name'],
            "team_id": tid,
            "position": last_row['position'],
            "proj_shots_p90": round(final_shots_p90, 2), # Pace
            "proj_shots_game": round(proj_shots_game, 2), # Volume (New)
            "proj_xg_p90": round(final_xg_p90, 2), # Pace
            "proj_xg_game": round(proj_xg_game, 2), # Volume (New)
            "proj_xa_p90": round(proj_xa_p90, 2),
            "proj_xg_chain_p90": round(proj_xg_chain_p90, 2),
            "shots_consistency": round(shots_std, 2),
            "prob_goal": float(round(prob_goal, 1)),
            "fair_odds_goal": fair_odds_goal,
            "prob_2_shots": float(round(prob_2_shots, 1)),
            "last_match_mins": int(last_row['minutes']),
            "avg_mins_l5": int(avg_mins_last_5),
            "sub_risk": sub_risk,
            "matchup_factor": round(matchup_multiplier, 2),
            "opp_defense": defense_rating,
            "sample_matches": len(player_df)
        }

    def scan_for_props_edges(self, target_team_id=None, min_minutes=300):
        """
        Scan all players.
        NOTE: Without a schedule of UPCOMING matches, we cannot apply opponent adjustments automatically here.
        This scan assumes 'Neutral' matchup (1.0x) unless updated to take a schedule dict.
        """
        # Calc Ratings First
        self.defense_ratings = self.get_team_defense_ratings()
        
        unique_players = self.data['player_name'].unique()
        projections = []
        
        for p_name in unique_players:
            p_mins = self.data[self.data['player_name'] == p_name]['minutes'].sum()
            if p_mins < min_minutes: continue
            
            # Base Projection (No Opponent known in generic scan)
            stats = self.get_player_rolling_stats(p_name)
            if stats:
                projections.append(stats)
                
        if not projections: return pd.DataFrame()
        return pd.DataFrame(projections)

if __name__ == "__main__":
    print("🧪 Testing Matchup Adjuster...")
    predictor = PlayerPropsPredictor(league="EPL", season="2025")
    
    if not predictor.data.empty:
        # Generate Ratings
        predictor.defense_ratings = predictor.get_team_defense_ratings()
        print(f"🛡️ League Avg xGA: {predictor.avg_league_xga:.2f}")
        
        # Get Top Defenses
        sorted_def = sorted(predictor.defense_ratings.items(), key=lambda x: x[1])
        print(f"🧱 Top 3 Defenses (Hardest): {sorted_def[:3]}")
        print(f"🕳️ Bottom 3 Defenses (Easiest): {sorted_def[-3:]}")
        
        # Test Player specific
        test_player = "Erling Haaland"
        if test_player in predictor.data['player_name'].values:
            print(f"\n🎯 Testing {test_player} vs Different Opponents:")
            
            # Neutral
            p_neutral = predictor.get_player_rolling_stats(test_player)
            print(f"   vs Neutral: {p_neutral['proj_xg_p90']} xG | {p_neutral['prob_goal']}% Goal Prob | {p_neutral['prob_2_shots']}% 2+ Shots Prob")
            
            # Hard
            hardest_team = sorted_def[0][0]
            p_hard = predictor.get_player_rolling_stats(test_player, upcoming_opponent=hardest_team)
            print(f"   vs {hardest_team} (Hard): {p_hard['proj_xg_p90']} xG | {p_hard['prob_goal']}% Goal Prob")
            
            # Easy
            easiest_team = sorted_def[-1][0]
            p_easy = predictor.get_player_rolling_stats(test_player, upcoming_opponent=easiest_team)
            print(f"   vs {easiest_team} (Easy): {p_easy['proj_xg_p90']} xG | {p_easy['prob_goal']}% Goal Prob")

