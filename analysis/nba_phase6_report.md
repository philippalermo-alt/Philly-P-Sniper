# 🧪 Phase 6 Experiments Report

**Date**: 2026-01-26

## 1. Track A: Matchups Ablation
Comparing Baseline (Rolling + Schedule) vs Matchup Candidates.

| Model Variant | LogLoss | Delta | Coin Flip ROI | Bet Count | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Phase 5)** | **0.5949** | - | -2.70% | 161 | 🔒 **Baseline** |
| **+ All Matchups** | 0.5967 | +0.0018 | +1.46% | 189 | ❌ Noise |
| **+ TOV Only** | 0.5967 | +0.0018 | **+4.80%** | 191 | ⚠️ High ROI / Low Precision |

**Analysis**:
*   `tov_mismatch` is a high-variance "Alpha Factor". It finds winners but hurts global calibration.
*   **Decision**: **HOLD**. Do not merge. We respect the "LogLoss" gate.

## 2. Track B: Totals Regression
Comparing Classification vs Regression Approach.

| Model Variant | Metric | Value | Book Value | ROI | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (ML Class)** | LogLoss | 0.7015 | 0.6923 | -9.53% | ❌ Toxic |
| **Regression (MAE)** | MAE | 15.40 | 14.59 | **-6.63%** | ❌ Better but Losing |

**Analysis**:
*   Regression improved ROI by +2.9%, but we are still fundamentally worse than the book (MAE +0.81 pts).
*   **Decision**: **ABANDON TOTALS**. We lack the predictive signal (Refs? Pace?).

## 3. Deployment Recommendation
Deploy **Phase 5 Baseline** (Moneyline w/ Schedule Features).
*   **ML ROI**: `-0.33%` (Global).
*   **Small Dog ROI**: `+3.3%` (Profitable).
*   **Safety**: Validated.

**Ready to Deploy**.
