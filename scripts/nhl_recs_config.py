
# NHL Recommendation Gates Configuration
# Version 1.0

GATE_VERSION = "1.0"

# Frozen Model Parameters (Phases 1-4)
MODEL_PARAMS = {
    'alpha_sog': 0.1393, # Updated 2026-01-28
    'alpha_ast': 0.1677, # Updated 2026-01-28
    'p_goal_default': 0.10 # Fallback if col missing
}

# 1. Eligibility Gates (Hard Filters)
ELIGIBILITY = {
    'min_toi': 14.0,           # Minutes
    'min_pp_share': 0.0,       # No strict cutoff generally, but checked for role
    'points_min_prob': 0.25,   # P(Points>=1)
    'points_min_mean': 0.60,
    'assists_min_prob': 0.20,  # P(Ast>=1)
    'goals_min_prob': 0.18,    # P(Goal>=1)
    'avg_goals_min_sog': 2.0,  # Min SOG Mean for Goal props
    'sog_min_buffer': 0.2      # Proj Mean >= Line + 0.2
}

# 2. Confidence Tiers
# Returns 'A', 'B', or 'C'
# Logic implemented in engine using these thresholds

TIER_THRESHOLDS = {
    'points_A': 0.40,
    'points_B': 0.25,
    
    'assists_A': 0.25,
    'assists_B': 0.20,
    
    'goals_A': 0.22,
    'goals_B': 0.18,
    
    # SOG is line-dependent
    'sog_2.5_A': 3.0,
    'sog_2.5_B': 2.7,
    
    'sog_3.5_A': 4.0,
    'sog_3.5_B': 3.6
}

# 3. EV/Edge Gates (The Trigger)
# (EV_decimal, Edge)
TRIGGERS = {
    'A': {'min_ev': 0.03, 'min_edge': 0.03},
    'B': {'min_ev': 0.05, 'min_edge': 0.05},
    'C': {'min_ev': 0.08, 'min_edge': 0.99} # C only allowed via exception
}

# 4. Tier C Exceptions
# Only allowed if: EV >= 0.08 AND TOI >= 16 AND NOT Bottom6
TIER_C_EXCEPTION = {
    'min_ev': 0.08,
    'min_toi': 16.0
}

# 5. Portfolio Controls (Max Recs per Market)
PORTFOLIO_MAX = {
    'SOG': 5,
    'GOALS': 3,
    'ASSISTS': 3,
    'POINTS': 3
}
