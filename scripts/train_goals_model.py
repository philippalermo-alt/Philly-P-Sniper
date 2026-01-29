
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import nbinom

FILE = "data/nhl_processed/goals_features.parquet"
SOG_MODEL_FILE = "data/nhl_processed/sog_projections_phase1_nb.csv" 
# Note: For strict Out-of-Sample, we need SOG Projections corresponding to the Test Set.
# The Phase 1 CSV contains projections for the Test Set (2025-09+).

def train_goals():
    print("🥅 Training Goals Model (Phase 2)...")
    df = pd.read_parquet(FILE)
    
    # 1. Prepare Data
    # Training: Use Actual SOG as 'n' trials.
    # Target: Goals.
    
    df['game_date'] = pd.to_datetime(df['game_date'])
    
    train = df[df['game_date'] < '2025-09-01'].copy()
    test = df[df['game_date'] >= '2025-09-01'].copy()
    
    # Filter Training for Non-Zero Trials
    train = train[train['shots'] > 0]
    # Test set? We predict based on features. 
    # But Binomial Model predicts 'p'.
    # We apply 'p' to Predicted SOG.
    # So Training must have info.
    
    print(f"Train (Shots>0): {len(train)} | Test: {len(test)}")
    
    # Features
    cols = ['ixg_per_shot_L10', 'pp_share_L10', 'opp_goalie_sv_pct', 'is_home']
    
    X_train = sm.add_constant(train[cols].astype(float))
    X_test = sm.add_constant(test[cols].astype(float))
    
    # Binomial Endog: [Success, Failure] = [Goals, Shots-Goals]
    # Note: Statsmodels Binomial expects [count_success, count_n] OR [count_success, count_failure]?
    # Documentation: "endog where the first column is the number of successes, and the second column is the number of failures" (if 2d array).
    
    y_train = pd.DataFrame({
        'success': train['goals'],
        'failure': train['shots'] - train['goals']
    })
    
    # If Shots < Goals (Data Error), clip failures to 0
    y_train['failure'] = y_train['failure'].clip(lower=0)
    
    # Fit GLM Binomial (Logit Link)
    model = sm.GLM(y_train, X_train, family=sm.families.Binomial()).fit()
    print("\n--- Model Summary ---")
    print(model.summary())
    
    # 2. Validation (Inference)
    # We need Projected SOG from Phase 1 for the Test Set.
    # Load Phase 1 Projections
    try:
        sog_proj = pd.read_csv(SOG_MODEL_FILE)
        # Join on Player, GameID? CSV has Player, Date.
        # Ensure Validation Set aligns.
        # Unique Key: PlayerName + Date.
        sog_proj['game_date'] = pd.to_datetime(sog_proj['game_date'])
        
        # Merge
        val_df = pd.merge(test, sog_proj[['player_name', 'game_date', 'pred_mu']], 
                          on=['player_name', 'game_date'], how='inner')
        print(f"Validation Metric Set: {len(val_df)} rows matched with SOG Projections.")
    except Exception as e:
        print(f"❌ Failed to load SOG Projections: {e}")
        return

    # Predict 'p' (Conversion Probability per Shot)
    # predict() returns probability of success
    val_df['pred_prob_goal'] = model.predict(sm.add_constant(val_df[cols].astype(float)))
    
    # Calculate P(Goal >= 1)
    # Using Negative Binomial SOG Distribution from Phase 1 Spec (Alpha = 0.1395)
    ALPHA = 0.1395
    n_nb = 1.0 / ALPHA
    
    def calc_prob_goal_ge_1(mu_sog, p_conv):
        # P(Goal >= 1) = 1 - Sum_k ( (1-p_conv)^k * P_NB(SOG=k) )
        # P_NB(k) is PMF of NegBin(n_nb, p_nb)
        # p_nb = n_nb / (n_nb + mu_sog)
        
        # We assume independent conversion trials.
        # E[ (1-p)^k ] for NB(r, p_nb) mgf-like logic?
        # Actually, simpler:
        # If Shots ~ NB and Goals|Shots ~ Binomial, then Goals ~ NB (roughly).
        # Goals Mean = mu_sog * p_conv.
        # Goals Variance > Poisson.
        # P(Goal=0) corresponds to "No Success".
        # P(Goal=0) = P(NB_successes=0) where parameter p_eff adjusted?
        # Let's use the explicit sum for first 20 terms (Probability Mass usually negligible after 20 shots).
        
        prob_0 = 0.0
        p_nb = n_nb / (n_nb + mu_sog)
        
        # Vectorized summation?
        # This function is row-wise.
        # Implement loop or approx.
        # Approx: Goals ~ Poisson(mu_sog * p_conv).
        # P(Goal>=1) = 1 - exp(-mu_sog * p_conv).
        # But we want to use the NB tail.
        
        # Exact Summation for k=0..20
        total_p0 = 0
        term_fail = 1 - p_conv
        
        # k=0: P(SOG=0) * 1
        # P(SOG=k) = nbinom.pmf(k, n_nb, p_nb)
        
        # This is slow row-wise.
        # Let's use Poisson Approx for MVP unless requested.
        # User: "Then combine with Phase 1 SOG distribution".
        # Let's use the "Poisson-Gamma mixture" property.
        # If SOG ~ Gamma-Poisson (NB).
        # Then Goals ~ Gamma-Poisson (NB) with mean scaled?
        # Yes. Goals is also NB with same 'alpha' but mean = mu * p.
        # Validated property of Thinned Poisson processes.
        # If X ~ NB(r, p_nb), and Y|X ~ Binom(X, p_conv).
        # Then Y ~ NB(r, p_new).
        # Mean Y = Mean X * p_conv.
        # Dispersion parameter 'alpha' (1/r) stays same.
        
        return 1 - nbinom.pmf(0, n_nb, n_nb / (n_nb + (mu_sog * p_conv)))

    # Vectorized NB Calc
    mu_goals = val_df['pred_mu'] * val_df['pred_prob_goal']
    p_nb_goals = n_nb / (n_nb + mu_goals)
    
    # P(Goal >= 1) = 1 - P(Goal=0)
    val_df['prob_goal_1plus'] = 1 - nbinom.pmf(0, n_nb, p_nb_goals)
    val_df['prob_goal_2plus'] = 1 - nbinom.cdf(1, n_nb, p_nb_goals)
    
    # Evaluation
    # Actual Goals >= 1
    val_df['act_goal_1plus'] = (val_df['goals'] >= 1).astype(int)
    
    # Brier Score
    brier = ((val_df['prob_goal_1plus'] - val_df['act_goal_1plus'])**2).mean()
    print(f"\n📉 Validation Metrics:")
    print(f"Brier Score: {brier:.4f}")
    
    # Calibration Buckets
    val_df['bucket'] = pd.cut(val_df['prob_goal_1plus'], bins=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0])
    calib = val_df.groupby('bucket')[['prob_goal_1plus', 'act_goal_1plus']].mean()
    calib['count'] = val_df.groupby('bucket')['prob_goal_1plus'].count()
    print("\n📊 Goal Calibration:")
    print(calib)
    
    # Save
    out_cols = ['player_name', 'game_date', 'pred_mu', 'pred_prob_goal', 'prob_goal_1plus', 'prob_goal_2plus']
    outfile = "data/nhl_processed/goal_projections_phase2.csv"
    val_df[out_cols].to_csv(outfile, index=False)
    print(f"\n💾 Projections Saved: {outfile}")

if __name__ == "__main__":
    train_goals()
