# NHL Phase 2 Totals: GO/NO-GO DECISION

**Date**: 2026-01-27
**Component**: NHL Totals Regression V2 (ElasticNet)
**Status**: **GO (RECOMMENDATIONS ONLY)**

## 1. Gate Checklist

| Gate | Description | Metric | Result |
|------|-------------|--------|--------|
| **1. Data Integrity** | Clean Room & Join Quality | 100% Match (Odds Era) | **PASS** |
| **2. Feature Safety** | Leakage Prevention | Strict `shift(1)` / 0% Future Data | **PASS** |
| **3. Model Skill** | Predictive Accuracy | Test MAE (1.850) < Book (1.859) | **PASS** |
| **4. Calibration** | Probability Accuracy | Bias 0.00 / Sigma 2.24 (Stable) | **PASS** |
| **5. Economics** | Profitability (Strategy B) | +2.2% ROI (Out-of-Sample) | **PASS** |

## 2. Approved Configuration (LOCKED)

The following parameters are **FROZEN** for Phase 1 Deployment:

- **Model**: ElasticNet (`alpha=0.1, l1_ratio=0.5`)
- **Features**: `nhl_totals_features_v1.csv` specification (L10 Rolling, Market, Rest)
- **Bias Correction**: `-0.1433` (Applied to Raw Prediction)
- **Sigma**: `2.2420` (Global)
- **Strategy**: **Strategy B**
    - **EV Threshold**: `> 5.0%`
    - **Odds Cap**: `Decimal <= 3.00` (+200)
    - **Side Selection**: Highest EV side only

## 3. Rollout Constraints (Phase 1)

1.  **Mode**: **RECOMMENDATIONS ONLY**
    - The system must **NOT** place bets automatically.
    - It should only log recommendations and send notifications.
2.  **Flagging**:
    - `NHL_TOTALS_V2_ENABLED` must default to `false`.
    - Enable only after EC2 proof-of-concept run.
3.  **Deployment Target**:
    - `utils/models/nhl_totals_v2.py` (New Inference Logic).
    - `pipeline/stages/process.py` (Integration).

## 4. Monitoring KPIs

| KPI | Threshold (Green) | Threshold (Red - Halt) |
|-----|-------------------|------------------------|
| **Calibration Bias** | +/- 0.05 Goals | > +/- 0.15 Goals |
| **Line Stability** | Sigma within 5% | Sigma shifts > 10% |
| **Win Rate (L100)** | > 52.0% | < 48.0% |
| **ROI (Season)** | > 0.0% | < -5.0% |

## 5. Verdict

**DECISION**: **PROCEED TO DEPLOYMENT**
**SCOPE**: Phase 1 (Shadow/Recommendations)
**STRATEGY**: B (EV > 5%)
