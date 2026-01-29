# 🧪 Phase 6 Track A: Matchups Report

**Status**: ⚠️ **Mixed Results** (Failed Strict Gates, Passed Profit).

## 1. Feature Tested: `tov_mismatch`
*   **Definition**: `h_sea_tov - a_sea_tov_forced`.
*   **Logic**: Sloppy Home Team vs Pressure Away Defense.

## 2. Gates
| Gate | Metric | Result | Target | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- |
| **1. ROI** | Coin Flip ROI | **+4.80%** | > +0.7% | ✅ **PASS** |
| **2. Precision** | LogLoss Delta | **+0.0018** | < -0.002 | ❌ **FAIL** |
| **3. Utility** | Importance Rank | **#12** | Top 15 | ✅ **PASS** |

## 3. Analysis
*   **ROI Explosion**: The feature acts as a powerful "Winning Edge" filter in the Coin Flip bucket, identifying profitable spots.
*   **LogLoss Noise**: Adding the feature made global probability calibration slightly worse (-0.18%).
*   **Decision**: **Do Not Merge** (Strict Adherence).
*   **Recommendation**: Use this feature in a "Specialist" model later, but do not pollute the General Baseline yet.

## 4. Pivot
Move to **Track B (Totals Rescue)**. Moneyline is safe (-0.3%). Totals are losing (-9.5%). Priority shifts to Track B.
