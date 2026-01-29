
# NHL OPS Configuration
# Centralized configuration for the Operational Pipeline

# Versioning
OPS_VERSION = "1.0.0"
PHASE1_VERSION = "1.0 (NB SOG)"
PHASE2_VERSION = "1.0 (Binomial Goals)"
PHASE3_VERSION = "1.0 (NB Assists)"
PHASE4_VERSION = "1.0 (Points Sim)"
GATE_VERSION = "1.0"

# Paths
DATA_DIR = "data/nhl_processed"
ARTIFACTS = {
    'sog': f"{DATA_DIR}/sog_projections.csv",
    'goals': f"{DATA_DIR}/goal_projections_phase2.csv",
    'assists': f"{DATA_DIR}/assist_projections_phase3.csv",
    'points': f"{DATA_DIR}/points_projections_phase4.csv",
    'recs': f"{DATA_DIR}/recommendations.csv",
    'audit': f"{DATA_DIR}/candidates_audit.csv",
    'daily': f"{DATA_DIR}/daily_projections.csv"
}

# Run Modes
# FULL: Strict data requirements.
# DEGRADED_NO_XG: Allow running without xG (uses naive avg).
# DEGRADED_NO_PP: Allow running without PP data.
RUN_MODES = ['FULL', 'DEGRADED_NO_XG', 'DEGRADED_NO_PP']
DEFAULT_MODE = 'FULL'

# Validation Thresholds (Hard Blockers)
THRESHOLDS = {
    'missing_sog_pct': 0.01, # Max 1% missing SOG
    'missing_toi_pct': 0.01,
    'join_mismatch_pct': 0.01,
    'dup_key_allowed': False
}

# Monitoring Alerts (Drift)
DRIFT_THRESHOLDS = {
    'calibration_mae': 0.03, # Max 3% diff in calibration bucket
    'consecutive_days': 2    # Alert if threshold exceeded N days
}

# Retraining
RETRAIN_CONFIG = {
    'cadence_days': 7,
    'min_new_games': 200,
    'promote_metrics': ['mae', 'brier', 'calibration_error']
}
