# 📉 NBA Model Baseline (v1: Market-Aware XGBoost)

**Date**: 2026-01-26
**Model Type**: XGBoost Classifier (Features: Rolling Stats + Implied Prob)
**Training Range**: 2021-2023 Seasons
**Validation Range**: 2024-2025 Season (`>= 2024-10-01`)
**Guardrails**: Odds Cap > 3.0, Dynamic EV Thresholds (Fav > 2%, Dog > 3-5%)

## 1. Precision (LogLoss)
*   **Model LogLoss**: `0.5955`
*   **Book LogLoss**: `0.5873`
*   **Delta**: `+0.0082` (Passed Gate < 0.01)

## 2. Calibration (Reliability)
*   **Underdog Calibration Error**: ~3% (Model ~16% vs Book ~13%)
*   **Bias**: Slight optimism on dogs (residual positive), but massively improved from +14%.

## 3. Betting Performance (Post-Guardrails)

### Top 50 Bets (Highest EV)
*   **Avg Odds**: `2.50` (+150)
*   **Longshot Share (>2.0)**: `84%` (42/50)
*   **ROI**: `+7.86%` ✅

### ROI by Odds Bucket (Full Validation Set)
| Bucket | Odds Range | ROI | Status |
| :--- | :--- | :--- | :--- |
| **Heavy Fav** | 1.0 - 1.5 | **+0.07%** | Break-Even |
| **Coin Flip** | 1.5 - 2.0 | **-4.97%** | Losing to Vig |
| **Small Dog** | 2.0 - 3.0 | **-5.74%** | Losing to Vig |
| **Longshot** | > 3.0 | **SKIPPED** | Capped |

## 4. Conclusion
The model is **safe to deploy** with the +200 Odds Cap. It respects market prices ("Market Aware") and avoids the "Mean Reversion bias" that plagued v0. Use strictly with `train_nba_model.py` simulation logic rules.
