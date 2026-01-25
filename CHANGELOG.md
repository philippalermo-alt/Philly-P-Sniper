# 📜 Change Log
All notable changes to the PhillyEdge.AI platform will be documented in this file.

## [2.1.0] - 2026-01-24
### Added (Model Optimizations)
- **NCAAB Calibration**: Implemented "Reality Cap" (Max Prob 65%) and "Noise Floor" (Min Edge 6%) to purge bad volume.
- **Smart Staking**: Dynamic Kelly Multipliers (NHL 2.0x, Soccer 1.5x) hardcoded into the API.
- **Soccer Enhancements**: Added "Stale Line Detector" and specialized "Draw Strategy" bucket (Odds > 3.10).
- **1H Pivot**: Logic to shift NCAAB volume to 1H if ROI > Full Game.
- **Totals Fix**: Patched `probability_models` with Implied Lambda solver to unlock lines 1.5, 3.5, 4.5.

## [2.0.0] - 2026-01-24
### Changed
- **Architecture**: Migrated from monolithic Streamlit to Client-Server (Next.js + FastAPI).
- **Backend API (`backend_api/`)**:
  - Implemented `/health` and `/opportunities` endpoints.
  - Ported "Top 15" edge logic and Sharp Intel scoring to pure Python API.
  - Removed Streamlit-specific caching issues (Bug-001 fixed permanently).
- **Frontend Client (`frontend_client/`)**:
  - Initialized Next.js 14 App Router with TypeScript.
  - Implemented **PhillyEdge Design System** (Dark/Gold Theme) via Tailwind V4.
  - Built "Command Center" Dashboard Shell with Skeleton Loaders and Status Strip.
- **Why**: To fix persistent caching bugs and enable advanced UI features (Instant Filters, Mobile Swipe) requested in 'Dashboard Rebuild'.

## [1.1.2] - 2026-01-24] - System Calibration & V2 Implementation

### 🏒 NHL Referee Model V2
*   **Implemented Regression Training**: Created `train_nhl_ref_model.py` to calculate adjustment factors from real 2025 data (Goals ~ Penalties) instead of heuristics.
*   **Pipeline Upgrade**: Updated `nhl_ref_expander.py` to scrape Game Scores (Home/Away) from ESPN, enabling regression analysis.
*   **Model Tuning**:
    *   Updated `TOTAL_ADJ_FACTOR` to **0.087** (from 0.20) based on regression results.
    *   **Disabled Margin Adjustment** (Set to 0.0) after regression showed negative correlation (Reverse Causality / "Game Management").
    *   **Safety Clip**: Added hard cap of **+/- 0.35 Goals** to total adjustments to prevent volatility.

### 🏀 NCAAB 1H Model (Leak Fixes)
*   **Leak Plugged**: Updated `probability_models.py` to strictly exclude `"1h"` markets from the V2 Model override.
*   **Calibration**:
    *   Raised `min_confidence` default from 75 to **80**.
    *   Raised `min_edge` default from 7% to **8.5%**.
*   **Safety Floor**: Updated `ncaab_h1_predict.py` to enforce a minimum StdDev of **6.5** points. This prevents the model from outputting 90%+ probabilities on volatile college games.
*   **Logic Fix**: Fixed "Dead Code" in `ncaab_h1_edge_finder.py` where the confidence threshold parameter was ignored.

### 📊 Dashboard & Logging
*   **Decimal Odds Fix**: Updated `ncaab_h1_edge_finder.py` to convert American Odds (e.g., -110) to Decimal (e.g., 1.91) before logging to DB.
*   **Stale Data Filter**: Updated `prop_sniper.py` to strictly filter out games that have already started (`kickoff < now`), cleaning up the Projections view.

### ⚽ Soccer Model V6 (Fix)
*   **Pipeline Fix**: The V6 xG Model predicts `Over 2.5` probability directly, but the main pipeline was ignoring this and trying to re-calculate using Poisson (and failing).
*   **Resolution**: patched `api_clients.py` to pass `prob_over` and `probability_models.py` to utilize it directly for Totals markets. Bets should now appear.


### 🛡️ Critical Infrastructure Patch (Afternoon Session)
*   **Props Engine Security ("Fail Closed")**:
    *   **The Issue**: If the Lineup API returned "None" (e.g. data missing), the system defaulted to placing bets, assuming all players were active.
    *   **The Fix**: Implemented a **Strict Fail-Closed** logic in `prop_sniper.py`. If lineups are required (imminent game) but unavailable, the bet is SKIPPED.
*   **Data Source Upgrade (API-Football)**:
    *   Replaced the unreliable ESPN Scraper with the official **API-Football** client (`lineup_client.py`).
    *   Added `utils.match_team` for fuzzy string matching (e.g., handling "Rennes" vs "Stade Rennais" mismatches).
*   **Dashboard Cleanup**:
    *   Updated `dashboard.py` to hide "PENDING" props for games that have already started (`kickoff > now`).
*   **Grading Reliability**:
    *   Fixed a `KeyError` crash in `bet_grading.py` that prevented the loop from processing subsequent bets.
    *   Expanded the grading lookback window from 24h to **72h** to catch late-settling or postponed games.
*   **Console Efficiency**:
    *   Filtered `hard_rock_model.py` output to suppress 0% edge / negative edge noise.

### 🏷️ Branding & Lineup Intelligence Fix (Evening Session)
*   **Rebranding (PhillyEdge.AI)**:
    *   Renamed Platform to **PhillyEdge.AI** across Dashboard `dashboard.py` and Headers.
    *   Renamed "Prop Sniper" to **"Prop Edge Engine"** to align with professional standards.
    *   Renamed "Draw Sniper" Strategy to **"Draw Edge Configuration"**.
    *   Renamed "Sniper Shortcuts" to `PHILLY_EDGE_SHORTCUTS.md`.
*   **Prop Edge Engine Bugfix**:
    *   **Finding**: The Prop Engine was passing the friendly League Name (e.g., "EPL") to the Lineup Client, which required the internal Key (e.g., "soccer_epl"). This caused ALL lineup checks to return `None`, incorrectly skipping valid props.
    *   **Resolution**: Patched `prop_sniper.py` to pass the correct `sport_key`. Lineup fetching is now operational for all supported leagues (EPL, Bundesliga, Ligue 1, etc.).
*   **Strategy Pivot**:
    *   Officially adopted the **"Precision Edge"** approach (Quality > Quantity), deprecating the "Spray and Pray" volume method.
    *   Renamed Platform to **PhillyEdge.AI** across Dashboard `dashboard.py` and Headers.

## [2.1.1] - 2026-01-25 - Emergency Recovery & Optimization
### 🚑 System Recovery
*   **Resolved Infinite Loop**: Diagnosed and fixed a critical failure loop caused by 100% Disk Usage. Use of `docker system prune -af` reclaimed 2.2GB and restored database stability.
*   **Deployment Optimization**: Analyzed `deploy_aws.sh` bottleneck. Created `deploy_fast.sh` which uses `.dockerignore` to reduce build context from **21GB** to **12MB**. Deployment time reduced from ~15 mins to ~2 mins.
*   **Calibration Upgrade**: Implemented **Logit Scaling** (Math Fix) to prevent probability "swapping" bugs.

### 🧹 Architecture Simplification
*   **Removed Legacy Frontend**: Deleted `frontend_client/` (Next.js/Tailwind) to align with Streamlit-only architecture.
*   **Docker Optimization**: Removed `client` service from `docker-compose.yml`, reducing resource usage and build times.
*   **Credential Synchronization**: Fixed mismatch between Docker defaults (`postgres`) and actual volume credentials (`user`). Ensured seamless connectivity for the API.

### 🐛 Bug Fixes (Stability & UX)
*   **[BUG-024] Dashboard Deduplication**: 
    *   **Issue**: Dashboard showed multiple cards for the same player prop if the scanner ran multiple times (e.g. "Haaland Goal" at 10:00 and 10:30).
    *   **Fix**: Implemented logic in `dashboard.py` to sort by `timestamp DESC` and drop duplicates based on unique `selection` + `teams` combination. Only the latest data is shown.
    *   **Context**: Fixes UI clutter; does not affect database integrity.
    
*   **[BUG-025] Infinite Swap Loop (Edge Flicker)**:
    *   **Issue**: The log was flooded with `[SWAP] Replacing Over 43.5 -> Under 43.5` loops. This occurred because both sides of a bet had similar positive edges (e.g. +5.1% vs +5.2%) due to minor model/odds oscillation, causing them to overwrite each other endlessly.
    *   **Fix**: Implemented an **"Edge Barrier"** in `probability_models.py`. The system now retrieves the *existing* bet's edge from the DB and only allows a replacement if the **New Edge > Old Edge + 0.5%**.
    *   **Context**: This prevents "lateral moves" where the model churns DB writes for negligible gain. Stability is now prioritized over micro-optimizations.

