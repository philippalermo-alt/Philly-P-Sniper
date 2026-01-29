# NHL Totals V2: Decommission Notes

## 1. Modifications

### A. Legacy Path (`processing/markets.py`)
*   **Action**: Hardened the existing exclusion block.
*   **Code Change**:
    ```python
    if sport == 'NHL':
        log("WARN", "NHL_TOTALS_LEGACY_ACTIVE (BLOCKED)")
        return None, None, None, None
    ```
*   **Impact**: Any attempt to use the legacy `calculate_match_stats` for NHL will trigger a explicit WARNING log and returning `None`, enforcing zero leakage.

### B. V2 Path (`pipeline/stages/process.py`)
*   **Action**: Added Proof Hooks.
*   **Code Change**:
    ```python
    if Config.NHL_TOTALS_V2_ENABLED:
        if 'NHL_V2_PROOF' not in context.metadata:
            log("PROOF", "NHL_TOTALS_V2_ACTIVE model=ElasticNet ...")
            context.metadata['NHL_V2_PROOF'] = True
    else:
        if 'NHL_DISABLED_PROOF' not in context.metadata:
            log("PROOF", "NHL Totals disabled (V2 flag off)")
            context.metadata['NHL_DISABLED_PROOF'] = True
    ```
*   **Impact**: Creates deterministic, grep-able proof of state in production logs.

## 2. Unreachable Code
*   The legacy NHL stats calculation logic in `processing/markets.py` (fetching `off_ypp`, etc.) is now physically unreachable for `sport='NHL'` due to the top-level guard clause.
*   We chose **Blocking** over **Deleting** to preserve the generic structure of the function for other sports (NBA/NCAAB) while explicitly carving out NHL.

## 3. Safety Verification
*   If `NHL_TOTALS_V2_ENABLED` is False (Default), the system logs "NHL Totals disabled" and skips all totals processing.
*   If True, it uses ONLY the `NHLTotalsV2` class.
