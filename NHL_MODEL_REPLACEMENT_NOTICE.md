# 🏒 NHL Model Replacement Declaration

**Effective Date:** 2026-01-27 (Upon completion of full odds backfill and final validation)  
**Status:** 🟢 **ACTIVE / SOLE SOURCE OF TRUTH**

## Summary
The NHL modeling system has undergone a full clean-room rebuild.  
The newly validated **NHL V2 model** fully replaces the prior NHL model.

## Scope
*   The previous NHL model is **retired and deprecated**.
*   All NHL recommendations now originate **exclusively from NHL V2**.
*   No legacy logic, parameters, or outputs are referenced or blended.

## Validation Basis
*   Trained on multi-season MoneyPuck-derived game data.
*   Validated against real historical closing odds.
*   Passed calibration, logloss, and ROI stability checks.
*   Backfill testing spans full seasons and multiple market regimes.

## Operational Rules
*   **NHL V2** is the only NHL model allowed in:
    *   `main.py`
    *   Scheduled scans
    *   Alerts
    *   Reporting
*   Any reintroduction of the legacy model requires **explicit user approval**.

## Intent
This deployment marks a structural replacement, not an iteration.  
All future NHL work builds on NHL V2.
