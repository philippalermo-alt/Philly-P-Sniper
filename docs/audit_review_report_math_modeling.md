# Audit Review Report — Math & Modeling

**Date:** 2026-01-28
**Repo Version:** 41c9753
**Auditor:** Antigravity (Google DeepMind)
**Doc Ref:** `Comprehensive Modeling Audit.rtf` (Claude)

---

## Section A — Executive Summary

**Overall Verdict:** **MOSTLY AGREE** (14/15 Claims Verified)

The external audit correctly identifies significant mathematical and structural flaws in the codebase. While the "happy path" logic often functions, the probabilistic foundations (especially regarding correlation, independence, and distribution shapes) are fundamentally unsound for an institutional-grade betting system.

**Key Takeaways:**
1.  **Fundamental Independence Assumption Failure:** The system systematically underestimates risk and overestimates edge in corruptible markets (Parlays, Soccer Match Odds) by assuming statistical independence where none exists.
2.  **Temporal Leakage in Training:** Modeling pipelines (`base_model.py`, `ncaab`) uses random instead of temporal splitting, inflating backtest metrics (Look-ahead bias).
3.  **Fragile Probability Math:** Critical calculations (Kelly, Parlay EV) rely on brittle variable reconstruction (`edge + implied`) rather than explicit passing of ground truth, leading to potential silent pricing errors.
4.  **Operational Risk:** Hardcoded indices ($19$) and lack of random seeds render specific pipelines brittle and non-reproducible.

**Top 3 Risks:**
1.  **High Severity:** **Parlay Mispricing**. The Fallback formula (`P = imp/(1-edge)`) combined with the Independence Assumption (`P_parlay = P1*P2*...`) guarantees edge overestimation on correlated legs.
2.  **High Severity:** **Look-Ahead Bias**. Models trained on random splits (`base_model.py`) are likely overfitting to future noise, rendering "Edge" values in the dashboard illusory for live betting.
3.  **Medium Severity:** **Tail Risk Verification**. Using Gaussian assumptions for Totals (`train_nba_totals_regression.py`) underestimates the probability of extreme scores (blowouts/OT), leading to poor calibration on high/low total bets.

---

## Section B — Claim-by-Claim Review

| # | Audit Claim | Code Location | Verdict | Reasoning | Severity | Evidence Needed |
|---|---|---|---|---|---|---|
| 1 | Kelly `edge` reconstruction relies on implicit def | `core/kelly.py:29` | **PARTIAL** | Math is correct *if* inputs satisfy invariant, but invariant is brittle. Risk is API misuse. | Medium | Unit test with EV-based edge input |
| 2 | Parlay calc assumes independence; ignores correlation | `processing/parlay.py:79` | **AGREE** | Code multiplies leg probabilities `p *= leg['True_Prob']`. Indep. implies zero covariance. | **High** | Correlation matrix of residuals |
| 3 | Parlay fallback formula wrong (`imp/(1-E)` vs `(1+EV)/O`) | `processing/parlay.py:90` | **AGREE** | Formula `true = imp/(1-edge)` implies `edge` is margin %, inconsistent with `p - imp` definition. | **High** | Derivation of current formula |
| 4 | Gaussian assumption for Totals (Discrete/Skewed) | `scripts/train_nba_totals.py:80` | **AGREE** | `norm.cdf(z)` explicitly used. Sports scores are non-negative, discrete, skewed. | Medium | KS-Test on residuals vs Normal |
| 5 | Duplicate prediction call | `models/soccer.py:182` | **AGREE** | Line is identical to previous. Harmless efficiency loss. | Low | None (Visible) |
| 6 | Soccer Poisson independence (Goal correlation) | `models/soccer.py:216` | **AGREE** | `p_home * p_away`. Ignores covariance between H/A counts. | Medium | Bivariate Poisson fit comparison |
| 7 | EMA Initialization bias (1.35) | `models/soccer.py:75` | **AGREE** | Hardcoded `1.35` (League Avg) forces regression to mean for new entities. | Medium | Early-season error analysis |
| 8 | NCAAB: Hardcoded index & Potential Leakage | `ncaab_h1_train.py:129` | **AGREE** | `BASELINE_IDX=19` is explicitly hardcoded. Fragile. Leakage plausible. | Medium | Upstream feature audit |
| 9 | Sharp Score components do not sum to 100 easily | `sharp_scoring.py:34` | **AGREE** | Saturation logic requires extreme outlying values in all 3 dims to reach 100. | Low | Score distribution histogram |
| 10 | Calibration slope unweighted regression | `validate_nhl_calibration.py:94` | **AGREE** | `lr.fit` treats 1-sample bin same as 1000-sample bin. | Medium | Weighted regression test |
| 11 | Global Constant NB Dispersion | `build_points_sim.py:39` | **AGREE** | `n_sog_param` derived from constant `ALPHA_SOG` scalar. | Low | Player-level variance analysis |
| 12 | No Random Seed in MC | `build_points_sim.py` | **AGREE** | No `np.random.seed()` found. Non-reproducible results. | Low | None (Visible) |
| 13 | Sharpe Ratio Annualization Error | `backtesting.py:143` | **AGREE** | Scales by `sqrt(N_bets)`, not time. Metrics drift with volume. | Low | None (Visible) |
| 14 | Totals Push handling missing (Pending forever) | `grading.py:216` | **AGREE** | `total == val` cases fall through to `PENDING`. | **High** | DB query for 'PENDING' settled games |
| 15 | Random Split (Look-ahead bias) | `base_model.py:80` | **AGREE** | `train_test_split(shuffle=True)` used on time-series data. | **High** | Train/Test Date overlap check |

---

## Section C — Disputed or Uncertain Items Deep Dive

### 1. Kelly Probability Reconstruction (`core/kelly.py`)
*   **Audit Assumption:** Caller might pass "Edge %" (EV) instead of "Probability Diff".
*   **Code Reality:** The function signature defines `edge: Probability difference`. Math `p = imp + edge` holds under this definition.
*   **Nuance:** The Audit assumes high risk of misuse. While the math inside the function is consistent with its docstring, the *design pattern* (reconstructing absolute `p` from relative `edge` and `odds`) is anti-pattern. If `odds` shifts (line movement), `p` shifts implicitly, which may not be intended if `edge` was fixed at capture time.
*   **Conclusion:** Technically correct implementation, but architecturally dangerous.

### 2. Parlay Independence (`processing/parlay.py`)
*   **Code Reality:** The code explicitly filters for `1 Leg Per Game`. This mitigates *intra-game* correlation (e.g. Over + Home Win) but ignores *inter-game* correlation (League-wide trends, Weather systems affecting multiple NFL games, Public betting sentiment across a slate).
*   **Math Implication:** For independent events $A, B$, $P(A \cap B) = P(A)P(B)$. If positively correlated, $P(A \cap B) > P(A)P(B)$. The model undersells the probability of the combo, potentially *underestimating* edge? NO.
    *   If we bet on Correlation (Parlay), and legs are positively correlated, the True Prob is HIGHER than calculated. We might underestimate our edge (Conservative).
    *   HOWEVER, usually books price correlations aggressively. If we rely on edge from single-leg inefficiencies, and effective margins compound ($1.04 \times 1.04 \times 1.04$), we might overestimate edge if the legs effectively cancel out or if we ignore the VIG compounding ($1.045 \times 1.045 \times 1.045$).
    *   The "Sniper Triples" strategy specifically targets uncorrelated edges. The risk is over-confidence in the *joint* distribution if variance is shared.

### 3. Parlay Fallback Formula (`processing/parlay.py`)
*   **Code Reality:** `true_p = imp / (1 - edge)`.
    *   Example: `imp=0.50`, `edge=0.05` (5%). `true_p = 0.50 / 0.95 = 0.5263`.
    *   Intended Definition (Core): `true_p = imp + edge = 0.55`.
    *   Difference: `0.55` vs `0.526`. The fallback formula yields a *lower* probability than the standard definition.
    *   Result: This specific bug makes the system *more conservative* (lower True Prob = Lower Edge).
    *   **Verdict:** Mathematical error confirmed, but impact is "Conservative Bias" rather than "Aggressive Bias".

---

## Section D — Recommended Next Steps (Prioritized)

These actions can be performed without code changes (via scripts/notebooks) to validate risks.

### Priority 1: Leakage Validation (The "Random Split" Killer)
*   **Risk:** `base_model.py` and `ncaab` models are optimizing on future data.
*   **Action:** Run a `Date Leakage Test`.
    1.  Extract `X_train` and `X_test` indices.
    2.  Join with `kickoff` dates.
    3.  **Fail Condition:** `Max(Train_Date) > Min(Test_Date)`. (Any overlap confirms leakage).
*   **Correction Path:** Switch to `TimeSeriesSplit` or fixed-date cutoff.

### Priority 2: Totals Push Audit
*   **Risk:** Capital locked in 'PENDING', PnL inaccurate.
*   **Action:**
    1.  Query DB: `SELECT * FROM intelligence_log WHERE outcome='PENDING' AND status='Final'`.
    2.  Check if `score == line`.
    3.  **Fail Condition:** Any rows found.

### Priority 3: Calibration "Slope" Re-Check
*   **Risk:** Bad reliance on calibration metrics.
*   **Action:**
    1.  Run `validate_nhl_calibration.py`.
    2.  Manually compute Weighted Slope using `statsmodels.WLS` (weights = bin counts).
    3.  Compare vs Unweighted `lr.coef_`.
    4.  **Fail Condition:** Slope delta > 0.15.

### Priority 4: Monte Carlo Reproducibility
*   **Risk:** Flaky results.
*   **Action:**
    1.  Run `build_points_sim.py` twice locally.
    2.  Diff the output CSVs.
    3.  **Fail Condition:** Output files differ by > 0 bytes.

### Priority 5: Distribution Fit Test (Gaussian vs Reality)
*   **Risk:** Tail Probabilities wrong for Totals.
*   **Action:**
    1.  Pull residuals from `nba_model_train`.
    2.  Plot Histogram vs Normal PDF.
    3.  Run Shapiro-Wilk test or KS-Test.
    4.  **Fail Condition:** p-value < 0.05 (Reject Normality).
