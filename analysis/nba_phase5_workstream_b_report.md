# 🧪 NBA Phase 5: Workstream B (Schedule/Rest) Report

**Date**: 2026-01-26
**Status**: ✅ **PASSED**
**Features Added**: `is_b2b`, `games_in_5`, `games_in_7` (Home/Away).
**Validation**: A/B Test vs Phase 4 Baseline.

## 1. Primary Goal: Coin-Flip Bucket (1.5-2.2 Odds)
*   **Baseline ROI**: `-5.93%` (163 Bets)
*   **New ROI**: `-2.74%` (161 Bets)
*   **Delta**: `+3.19%` (Target > 2.0%) ✅
*   **Outcome**: The schedule features successfully improved the coin-flip performance, likely by identifying "Schedule Losses" (Fatigue).

## 2. Mechanism of Action
*   **Avoided Bets**: 35 Bets were dropped by the new model.
*   **ROI of Avoided Bets**: `-37.63%`.
*   **Insight**: The model learned to *avoid* tired teams that the Baseline model mistakenly bet on. This "Trap Avoidance" is the primary driver of alpha.

## 3. Safety Check (Gate 0)
*   **Avg Odds**: `1.90` (Safe/Sharpshooter profile).
*   **Longshots (>3.0)**: `0` (Capped).

## 4. Regression Check (Gate 2)
*   **Global LogLoss**: `0.5950` vs `0.5955` (Improved).
*   **Regression**: None.

## 5. Recommendation
**MERGE** logic into production pipeline.
