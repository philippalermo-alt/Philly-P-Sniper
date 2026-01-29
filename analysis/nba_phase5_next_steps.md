# 🧭 NBA Phase 5 Next-Steps: The Road to Profit

**Current Status**:
*   **Moneyline**: `ROI -0.33%` (Viable). Dog Bucket `+3.3%` (Profitable).
*   **Totals**: `ROI -9.53%` (Toxic).

## TRACK A: Moneyline Improvements (Workstream C - Matchups)
**Goal**: Turn the Coinflip bucket (-0.8%) into PROFIT by modeling mismatches.

### 1. The Strategy: Difference/Ratio Features (Delta)
*   **Concept**: Instead of raw levels, model the *gap* between Offense and Defense.
*   **Features**:
    *   `reb_mismatch`: `h_sea_orb - a_sea_opp_orb` (Home ORB rate vs Away Allowed ORB).
    *   `tov_mismatch`: `h_sea_tov - a_sea_tov_forced` (Home Sloppiness - Away Pressure).
    *   `three_pt_mismatch`: `h_sea_3par - a_sea_opp_3par` (3pt Frequency Delta).
    *   `pace_interaction`: `h_sea_pace * a_sea_pace` (Product remains for pace).

### 2. Validation Gates (Strict)
*   **Gate 1 (Coin Flip ROI)**: Must improve by **≥ +1.5%** absolute (Target > +0.7%).
*   **Gate 2 (Coin Flip LogLoss)**: Must improve by **≥ 0.002**.
*   **Gate 3 (Volume)**: Bet count change within ±15% (No volume collapse).
*   **Sanity Check (Ablation)**: At least 2 new features must appear in Top 15 Feature Importance (SHAP/Gain).

---

## TRACK B: Totals Rescue Plan (Regression Pivot)
**Goal**: Stop losing -9% on Totals.

### 1. Proposal: Regression Target
*   **Target**: Predict `total_points` (Continuous).
*   **Metric**: MAE (Mean Absolute Error).
*   **Sigma**: Estimate dynamic Sigma from training residuals (Do not hardcode 18.5).
*   **Betting Logic**: `Prob_Over = CDF((Pred - Line) / Sigma)`.

### 2. Validation Gates
*   **Metric**: `Model_MAE < Book_MAE * 1.05`.
*   **Residuals**: Mean ≈ 0. Distribution Normal.
*   **Leakage Test**: Ensure features (e.g. `total_line`) are NOT used in the regression target formulation improperly (features ok, target no).

---

## 🚀 Execution Order
1.  **Workstream C (Matchups)**:
    *   **Step 1**: Update `build_nba_features.py` to include `opp_tov`, `opp_orb` in rolling stats (Missing currently).
    *   **Step 2**: Calculate Deltas.
    *   **Step 3**: Run A/B Sandbox.
2.  **Track B (Totals)**: Only if Track A passes.
3.  **Deployment**: No deploy without Docker Proof.
