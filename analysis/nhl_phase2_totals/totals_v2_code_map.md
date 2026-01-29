# NHL Totals V2: Code Map & Inventory

## 1. Legacy Path (Decommissioned)
*   **File**: `processing/markets.py`
*   **Function**: `calculate_match_stats`
*   **Status**: **HARD DISABLED**
*   **Logic**:
    ```python
    if sport == 'NHL':
        # DEPRECATED: Legacy NHL Model Retired (2026-01-27)
        return None, None, None, None
    ```
*   **Call Graph**:
    *   Called by `process_match` (Generic Sports path).
    *   Since it returns `None`, no Opportunity is created for NHL Totals via this path.

## 2. V2 Path (Active)
*   **File**: `pipeline/stages/process.py` (Stage 4)
*   **Function**: `NHLTotalsV2.predict`
*   **Class**: `utils.models.nhl_totals_v2.NHLTotalsV2`
*   **Trigger**:
    *   Iterates `context.odds_data['NHL']`.
    *   Checks `Config.NHL_TOTALS_V2_ENABLED`.
    *   Calls `_nhl_totals.predict(...)`.
*   **Logic**:
    *   Loads `models/nhl_totals_v2.joblib` (ElasticNet).
    *   Applies Bias Correction (`-0.1433`) and Sigma (`2.2420`).
    *   Returns Recommendation if EV > 5% (Strategy B).

## 3. Findings
*   **Overlap**: None. Legacy path is explicitly blocked for 'NHL' sport key.
*   **Leakage Risk**: Low. Legacy code exists but constitutes a dead branch for NHL.
*   **Control**: V2 is the *only* functional path, gated by `NHL_TOTALS_V2_ENABLED`.
