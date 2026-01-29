
import pandas as pd
import numpy as np
import scipy.stats as stats

# Constants from Frozen Specs
ALPHA_SOG = 0.1395
ALPHA_AST = 0.1680
N_SIMS = 10000

def run_simulation():
    print(f"🎲 Starting Points Simulation (N={N_SIMS})...")
    
    # 1. Load Data
    p1 = pd.read_csv("data/nhl_processed/sog_projections_phase1_nb.csv")
    p2 = pd.read_csv("data/nhl_processed/goal_projections_phase2.csv")
    p3 = pd.read_csv("data/nhl_processed/assist_projections_phase3.csv")
    
    # Rename Cols to avoid collision
    p1 = p1.rename(columns={'pred_mu': 'mu_sog'})
    p2 = p2.rename(columns={'pred_prob_goal': 'p_goal', 'pred_mu': 'mu_sog_check'}) 
    p3 = p3.rename(columns={'pred_mu': 'mu_ast'})
    
    # Merge
    # P2/P1 keys: player_name, game_date. (Team/Opponent also in P1)
    df = pd.merge(p1, p2[['player_name', 'game_date', 'p_goal']], on=['player_name', 'game_date'], how='inner')
    df = pd.merge(df, p3[['player_name', 'game_date', 'mu_ast']], on=['player_name', 'game_date'], how='inner')
    
    print(f"Merged Data: {len(df)} rows.")
    
    # 2. Vectorized Simulation
    n_rows = len(df)
    
    # --- Step A: SOG (Negative Binomial) ---
    # Scipy nbinom args: n, p
    # n = 1/alpha
    # p = n / (n + mu)
    
    n_sog_param = 1.0 / ALPHA_SOG
    p_sog_param = n_sog_param / (n_sog_param + df['mu_sog'].values)
    
    # Generate (Rows x Sims) matrix
    # Note: numpy random negative_binomial uses (n, p).
    # "successes" -> output. 
    # Definition check: Scipy/Numpy 'n' is number of successes, 'p' is probability of success.
    # Result is number of failures? 
    # Validating Scipy/Numpy defs vs NB2.
    # NB2: Var = mu + alpha*mu^2.
    # Scipy: nbinom.rvs(n, p) mean is n(1-p)/p.
    # Our formula: mu. n(1-p)/p = mu -> n(1 - n/(n+mu)) / (n/(n+mu)) = mu. Correct.
    
    print("  Simulating SOG...")
    # Reshape for broadcasting
    n_sog_mat = np.full((n_rows, 1), n_sog_param)
    p_sog_mat = p_sog_param.reshape(-1, 1)
    
    # Sim:
    # np.random.negative_binomial(n, p)
    # We broadcast: (Rows, 1) input -> (Rows, N_SIMS) output?
    # Numpy nbinom supports array_like inputs.
    # We create (Rows,) array and request size=(Rows, Sims)? No, size must act weird.
    # Easiest: Loop or Batched?
    # Or just pass (Rows,) arrays and size=(N_SIMS, Rows).T?
    # Can np.random.negative_binomial take arrays for n and p? YES.
    # So we simply do:
    # sim_sog = np.random.negative_binomial(n_sog_param, p_sog_param, size=(N_SIMS, n_rows)).T
    # Wait, n_sog_param is scalar. p_sog_param is array (n_rows,).
    # size=(N_SIMS, n_rows)? The args must broadcast to size.
    # If p_sog_param is (n_rows,), broadcasting to (N_SIMS, n_rows) requires p to be (1, n_rows)?
    
    # Let's align dimensions.
    # p_sog_broad = df['mu_sog'].values # Placeholder name
    # Actually, simpler:
    sim_sog = np.empty((n_rows, N_SIMS), dtype=int)
    # Numpy's generator might be finicky with broadcasting large arrays.
    # Let's use `scipy.stats.nbinom.rvs`.
    
    # Optimized:
    # p_sog_param is shape (n_rows,).
    # We want (n_rows, N_SIMS).
    # nbinom.rvs(n, p, size=(N_SIMS, n_rows))?
    # If n and p are arrays, size must match?
    # Actually, iterate? 10,000 rows is small. 10,000 sims is large.
    # 10k x 10k = 100M elements. 800MB RAM. Feasible.
    
    # Let's generate in chunks if needed, but 100M ints is fine.
    
    sim_sog = stats.nbinom.rvs(n_sog_param, p_sog_param.reshape(-1, 1), size=(n_rows, N_SIMS))
    
    # --- Step B: Goals | SOG (Binomial) ---
    print("  Simulating Goals...")
    # Binomial(n=SOG, p=p_goal)
    p_goal = df['p_goal'].values.reshape(-1, 1)
    sim_goals = np.random.binomial(sim_sog, p_goal)
    
    # --- Step C: Assists (Negative Binomial) ---
    print("  Simulating Assists...")
    n_ast_param = 1.0 / ALPHA_AST
    p_ast_param = n_ast_param / (n_ast_param + df['mu_ast'].values)
    
    sim_assists = stats.nbinom.rvs(n_ast_param, p_ast_param.reshape(-1, 1), size=(n_rows, N_SIMS))
    
    # --- Step D: Points ---
    print("  Calculating Points...")
    sim_points = sim_goals + sim_assists
    
    # --- Step E: Aggregation ---
    print("  Aggregating...")
    # Mean
    df['proj_points_mean'] = sim_points.mean(axis=1)
    
    # Probs (Vectorized)
    df['prob_points_1plus'] = (sim_points >= 1).mean(axis=1)
    df['prob_points_2plus'] = (sim_points >= 2).mean(axis=1)
    
    # --- Step F: Validation ---
    print("\n📊 Validation (Points):")
    # Actual Points? Need 'goals' and 'assists' actuals.
    # We need to load Actuals. 
    # Merging with Goals/Assists features?
    # P1/P2/P3 CSVs did NOT save actuals (in the projection file).
    # We must load actuals from DB/Features to validate.
    # Let's load `nhl_processed/goals_features.parquet` (Goals) and `assists_features.parquet` (Assists).
    
    gf = pd.read_parquet("data/nhl_processed/goals_features.parquet")
    af = pd.read_parquet("data/nhl_processed/assists_features.parquet")
    
    # Merge Actuals to DF
    # Keys: player_name, game_date.
    
    # Ensure Datetime
    gf['game_date'] = pd.to_datetime(gf['game_date'])
    af['game_date'] = pd.to_datetime(af['game_date'])
    
    gf['game_date'] = gf['game_date'].dt.strftime('%Y-%m-%d')
    af['game_date'] = af['game_date'].dt.strftime('%Y-%m-%d')
    
    df = pd.merge(df, gf[['player_name', 'game_date', 'goals']], on=['player_name', 'game_date'], how='left')
    df = pd.merge(df, af[['player_name', 'game_date', 'assists']], on=['player_name', 'game_date'], how='left')
    
    df['act_points'] = df['goals'] + df['assists']
    df['act_points_1plus'] = (df['act_points'] >= 1).astype(int)
    
    # Brier
    brier = ((df['prob_points_1plus'] - df['act_points_1plus'])**2).mean()
    print(f"Brier Score: {brier:.4f}")
    
    # Buckets
    df['bucket'] = pd.cut(df['prob_points_1plus'], bins=[0, 0.2, 0.4, 0.6, 1.0])
    calib = df.groupby('bucket')[['prob_points_1plus', 'act_points_1plus']].mean()
    calib['count'] = df.groupby('bucket')['prob_points_1plus'].count()
    print(calib)
    
    # --- Step G: Operational Safeguards ---
    print("\n🔒 Applying Operational Safeguards...")
    
    # 1. Load Context for Tiers (PP Share from Goals Features)
    # We already loaded 'gf' for validation.
    # gf has 'game_date', 'player_name', 'pp_share_L10' (Need to ensure it was saved in GF).
    # Check build_nhl_goals_features.py: 'pp_share_L10' IS in cols.
    
    # Merge values
    df = pd.merge(df, gf[['player_name', 'game_date', 'pp_share_L10']], 
                  on=['player_name', 'game_date'], how='left')
    df['pp_share_L10'] = df['pp_share_L10'].fillna(0)
    
    # 2. Eligibility Filter
    # Rule: Mean >= 0.6 OR Prob(1+) >= 25%
    df['is_priceable'] = (df['proj_points_mean'] >= 0.6) | (df['prob_points_1plus'] >= 0.25)
    
    # 3. Confidence Tiers
    # Tier A: Superstars (Mean >= 0.9) OR Top PP (Share >= 0.40)
    # Tier B: Priceable (Meets Eligibility)
    # Tier C: Bottom-6 (Not Priceable)
    
    def get_tier(row):
        if not row['is_priceable']:
            return 'C'
        if row['proj_points_mean'] >= 0.9 or row['pp_share_L10'] >= 0.40:
            return 'A'
        return 'B'

    df['tier'] = df.apply(get_tier, axis=1)
    
    # Validation by Tier
    print("\n📊 Calibration by Tier:")
    for tier in ['A', 'B', 'C']:
        subset = df[df['tier'] == tier]
        if len(subset) == 0: continue
        
        pred = subset['prob_points_1plus'].mean()
        act = subset['act_points_1plus'].mean()
        delta = pred - act
        count = len(subset)
        
        status = "✅" if abs(delta) < 0.03 else "⚠️"
        print(f"  Tier {tier} ({count} rows): Pred {pred:.3f} | Act {act:.3f} | Delta {delta:+.3f} {status}")

    # --- Save ---
    outfile = "data/nhl_processed/points_projections_phase4.csv"
    out_cols = ['player_name', 'game_date', 'tier', 'is_priceable', 
                'mu_sog', 'p_goal', 'mu_ast', 'pp_share_L10',
                'proj_points_mean', 'prob_points_1plus', 'prob_points_2plus']
                
    df[out_cols].to_csv(outfile, index=False)
    print(f"\n💾 Points Projections Saved (Safeguarded): {outfile}")

if __name__ == "__main__":
    run_simulation()
