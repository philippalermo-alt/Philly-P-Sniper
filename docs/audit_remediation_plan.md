# Audit Remediation Plan: Math & Modeling

**Date:** 2026-01-29
**Status:** Proposal for User Review
**Based on:** `docs/audit_review_report_math_modeling.md`

This plan outlines the prioritized actions required to address the critical mathematical and structural flaws identified in the system audit.

---

## Phase 1: Critical Integrity & Settlement (IMMEDIATE PRIORITY)
**Goal:** Ensure the numbers we see are real (not future-peeking) and that capital is correctly settled.

### 1.1 Fix Temporal Leakage in Backtesting
*   **Issue:** `base_model.py` and `ncaab` pipelines use `train_test_split(shuffle=True)`. This trains the model on future games (e.g., training on Feb 2025 to predict Jan 2025), artificially inflating accuracy and "Edge".
*   **Recommended Fix:**
    *   Implement `TimeSeriesSplit` or a strict Date Cutoff (e.g., `Train < 2024-01-01`, `Test >= 2024-01-01`).
    *   Enforce a `validate_no_leakage()` check in the training pipeline that asserts `max(train_date) < min(test_date)`.
*   **System Impact:**
    *   **⚠️ Expect Drops in Metrics:** "Win Rates" and "ROI" in backtests will likely drop significantly as they face reality. This is not a regression; it is a correction of a hallucination.
    *   **Model Re-Training:** All models inheriting from `BaseModel` must be retrained.

### 1.2 Resolve "Pending" Totals (Push Handling)
*   **Issue:** `grading.py` fails to handle cases where `Score == Total` (exact push) for Over/Under bets, leaving them as `PENDING` indefinitely.
*   **Recommended Fix:**
    *   Update `grading.py` logic to explicitly check `if total == val: return 'PUSH'`.
    *   Run a migration script to backfill/settle all historically stuck bets.
*   **System Impact:**
    *   **Bankroll Update:** Capital currently locked in limbo will be released.
    *   **Record Accuracy:** Win/Loss records in the dashboard will update immediately.

---

## Phase 2: Mathematical Correctness (HIGH PRIORITY)
**Goal:** Ensure pricing and probabilities are mathematically sound to prevent "Edge" miscalculation.

### 2.1 Fix Parlay Probability Fallback
*   **Issue:** The fallback formula `True_Prob = Implied / (1 - Edge_Pct)` is mathematically wrong and derives a lower probability than intended.
*   **Recommended Fix:**
    *   Replace with the correct inversion of the EV formula: `True_Prob = (1 + EV) / Decimal_Odds`.
    *   Or, strictly use `Implied_Prob + Edge_Probability_Diff` if available.
*   **System Impact:**
    *   **Edge Adjustment:** Calculated "Edge" on parlay suggestions will change (likely increase slightly).
    *   **Risk Profile:** We will be betting slightly more aggressively on parlays.

### 2.2 Mitigate Correlation Risk in Parlays
*   **Issue:** Multiplying probabilities (`P1 * P2 * P3`) assumes independence. If legs are positively correlated (common in sports), true probability is higher (good), but if we are betting *against* correlation, we are exposed.
*   **Recommended Fix:**
    *   **Block Same-Game Parlays (SGP):** Enforce a strict "1 Leg Per EventID" rule in `parlay.py` (Current code attempts this, but needs verification).
    *   **Correlation Penalty:** Apply a 5-10% "uncertainty haircut" to the calculated Edge for multi-leg bets to account for hidden inter-game correlations.
*   **System Impact:**
    *   **Fewer Recommendations:** The hurdle rate for Parlays will be harder to hit.

### 2.3 Correct Kelly Input Logic
*   **Issue:** `kelly.py` implicitly assumes `edge` is a probability difference, but nomenclature varies across the system (sometimes EV %).
*   **Recommended Fix:**
    *   Rename argument to `prob_diff` to be explicit.
    *   Add validation: `assert -1.0 <= prob_diff <= 1.0`.
    *   Add support for calculating from EV directly: `calculate_kelly_from_ev(ev, odds)`.
*   **System Impact:**
    *   **Defensive Coding:** Prevents future bugs where a 5% EV is treated as a +5% probability boost (which would be huge).

---

## Phase 3: Operational Hardening (MEDIUM PRIORITY)
**Goal:** Improve reliability, reproducibility, and monitoring.

### 3.1 Hardening NCAAB Pipelines
*   **Issue:** Hardcoded index `BASELINE_IDX = 19` in `ncaab_h1_train.py` is brittle. If feature order changes, the model breaks silently.
*   **Recommended Fix:**
    *   Use Pandas column names (`df['pace_adjusted']`) instead of numpy array indices for model inputs.
*   **System Impact:**
    *   **Stability:** Pipeline becomes robust to feature addition/removal.

### 3.2 Enforce Reproducibility
*   **Issue:** Monte Carlo simulations (`build_points_sim.py`) lack random seeds.
*   **Recommended Fix:**
    *   Set `np.random.seed(42)` at the start of all simulation scripts.
*   **System Impact:**
    *   **Debugging:** We can finally reproduce "weird" results exactly.

### 3.3 Validate Distribution Assumptions
*   **Issue:** Totals model assumes Gaussian distribution.
*   **Recommended Fix:**
    *   Run a Kolmogorov-Smirnov (KS) test on residuals.
    *   If non-normal, switch to Quantile Regression or a Poisson-based approach for Totals.
*   **System Impact:**
    *   **Accuracy:** Better calibration on extreme lines (blowouts).

---

## Summary of Work
1.  **Phase 1** must be done immediately to stop "lying" to ourselves about model performance.
2.  **Phase 2** fixes the pricing engine to stop "lying" to the bankroll.
3.  **Phase 3** ensures the system doesn't break when we touch it next.

**Next Step:** Awaiting user approval to begin **Phase 1**.
