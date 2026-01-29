# Antigravity Quick Reference Guide

> **System Status**: Mixed (Cron Migrated to Server, Audit in Progress)
> **Last Updated**: 2026-01-28
> **Maintainer**: Antigravity AI

## 1. System Overview

### Architecture
*   **Core**: Python 3.12 (Dockerized `philly_p_api`).
*   **Database**: PostgreSQL 17 (Dockerized `philly_p_db`).
*   **Orchestration**:
    *   **Primary**: Cron (EC2 Host) -> Docker Exec -> Python Wrapper.
    *   **Advanced**: Systemd (EC2 Host) -> Docker Exec -> Python Scripts (NHL/NBA V2).
*   **Frontend**: Streamlit (`web/dashboard.py`).
*   **Deployment**: Shell Scripts (`deploy_cron.sh`, `deploy_ec2.sh`) + SCP/Rsync.

### Infrastructure
*   **Host**: EC2 Instance (`100.48.72.44` via Tailscale).
*   **User**: `ubuntu`.
*   **Root Dir**: `/home/ubuntu/Philly-P-Sniper`.
*   **Logs**:
    *   Unified App Logs: `logs/app.log` (Volume Mounted).
    *   Cron Logs: `logs/cron_*.log` (Host-level redirects).

---

## 2. Workflows (A-Z)

### Ingest Outcomes
**ID**: `cron-ingest`
**Status**: Active
**Schedule**: 23:00, 03:00 EST
**Purpose**: Update pending bets with final scores to calculate Profit/Loss.
**Trigger**: `run_ingest_daily.sh`
**Process Flow**:
1.  Wrapper acquires lock.
2.  `main.py --ingest` executed.
3.  Fetches scores from `OddsAPI` (or fallback).
4.  Updates `intelligence_log` (Win/Loss).
5.  Refreshes `calibration_log`.
**Dependencies**: OddsAPI, PostgreSQL.
**Error Handling**: Logs to `cron_ingest.log`. No automatic retry.

### NHL/NBA V2 Operations (Systemd)
**ID**: `systemd-v2-ops`
**Status**: Active
**Type**: Systemd Services + Timers.
**Location**: `ops/systemd/`
**Components**:
- `nhl-odds-ingest`: High-frequency odds fetch.
- `nhl-totals-run`: Model inference.
- `nhl-totals-retrain`: Weekly retraining.
- (NBA equivalents).
**Trigger**: Systemd Timers (Managed by OS).
**Process**: Executes specific python modules (e.g., `python -m ops.nhl_v2.run`) inside the Docker container.

### Pipeline (Hourly)
**ID**: `cron-pipeline`
**Status**: Active
**Schedule**: Hourly (09:00 - 21:00 EST)
**Purpose**: Scan for new value bets (Edges).
**Trigger**: `run_pipeline_hourly.sh`
**Process Flow**:
1.  Wrapper acquires lock.
2.  Exports V2 Flags (`NHL_TOTALS_V2_ENABLED=true`).
3.  `main.py` executed.
4.  Fetches Odds (OddsAPI) + Splits (ActionNetwork).
5.  Runs Models (XGBoost/Residual).
6.  Filters Edges (> X% EV).
7.  Writes to DB & Broadcasts (Telegram/Twitter).
**Dependencies**: ActionNetwork (Cookie), OddsAPI, Twitter API, Telegram API.
**Knowledge Gaps**: Exact threshold for broadcasting vs just logging.

### Recap (Daily)
**ID**: `cron-recap`
**Status**: Active
**Schedule**: 07:00 EST
**Purpose**: Summary of yesterday's performance.
**Trigger**: `run_recap_daily.sh`
**Process Flow**:
1.  Queries `intelligence_log` for yesterday's settled bets.
2.  Generates P&L graphic (assumed).
3.  Posts to Twitter/Telegram.

### Settlement
**ID**: `cron-settle`
**Status**: Active
**Schedule**: 04:30 EST
**Purpose**: Specialized settlement (Redundant to Ingest?). relies on ESPN?
**Trigger**: `run_settle_daily.sh`
**Knowledge Gaps**: Why does this exist alongside `Ingest`? Code suggests it might use ESPN "Hidden" API for props?

### Weekly Retraining
**ID**: `cron-retrain`
**Status**: Active
**Schedule**: Mondays 06:00 EST
**Purpose**: Retrain ML models with latest data.
**Trigger**: `run_retrain_weekly.sh`
**Input**: Last 7 days of data added to training set.
**Output**: New model `.pkl` files (or DB weights).

---

## 3. Integration Inventory

### Action Network (Unofficial)
*   **Purpose**: "Sharp Money" signals (Ticket % vs Money %).
*   **Auth**: `ACTION_COOKIE` (Browser Cookie, High Fragility).
*   **Risk**: Cookie expiration breaks this instantly.
*   **Endpoints**: `/nba/public-betting.json`, etc. (Reverse Engineered).

### ESPN (Hidden)
*   **Purpose**: Live Scores / Settlement fallback.
*   **Auth**: Public (None), but endpoint schema changes often.
*   **Status**: Used in Dashboard & Settlement.

### The-Odds-API (Official)
*   **Purpose**: Primary source for Odds, Lines, and Bookmaker data.
*   **Auth**: API Key (`ODDS_API_KEY`).
*   **Limits**: Paid Tier (props support confirmed).

### API-Football (Official)
*   **Purpose**: Soccer Lineups and Stats (xG).
*   **Auth**: API Key (`FOOTBALL_API_KEY`).
*   **Usage**: `data/clients/football_api.py`.

### KenPom (Official)
*   **Purpose**: NCAAB Advanced Metrics (Efficiency, Tempo).
*   **Auth**: API Key (`KENPOM_API_KEY`).
*   **Usage**: `data/clients/ncaab_api.py` (assumed).

### SMTP Email
*   **Purpose**: Daily Recap Emails or Alerts.
*   **Auth**: `EMAIL_USER` + `EMAIL_PASSWORD`.
*   **Host**: `smtp.gmail.com` (587).
*   **Recipient**: `EMAIL_RECIPIENT`.

### Telegram
*   **Purpose**: Admin Alerts & User Notifications.
*   **Auth**: Bot Token + Chat ID.
*   **Risk**: No Retry logic (Network blip = missing alert).

### Twitter (X)
*   **Purpose**: Public broadcasting of picks.
*   **Auth**: OAuth 1.0a (Consumer Key/Secret + Access Token/Secret).
*   **Library**: `tweepy`.

---

## 4. Troubleshooting Index

#### "Operation not permitted" in Cron Logs
*   **Cause**: Attempting to run cron on macOS Local Machine.
*   **Fix**: Run `scripts/deploy_cron.sh` to move to EC2. Clear local crontab.

#### "Action Cookie Expired"
*   **Symptom**: "PermissionError" or 401/403 in `action_network.py`.
*   **Fix**:
    1.  Login to ActionNetwork in Browser.
    2.  Copy new `cookie` header.
    3.  Update `.env` -> `ACTION_COOKIE`.
    4.  Restart API (`docker-compose restart api`).

#### Dashboard "Connection Closed"
*   **Symptom**: Streamlit Admin Dashboard freezes or crashes.
*   **Cause**: DB Connection exhaustion (Finding #3).
*   **Fix**: Restart container (`docker-compose restart api`). Long term: Fix Code.

#### Dashboard "Over/Under" Missing Line Number
*   **Symptom**: Dashboard displays "Over" or "Under" without the line value (e.g., just "Over" instead of "Over 6.5").
*   **Cause**: `pipeline/stages/process.py` omitting line data in `selection` string.
*   **Fix**: Ensure `selection` includes the line: `f"{recommendation} {line}"`.
*   **Ref**: Incident 2026-01-28 (Fixed in `process.py`).

---

#### NHL Totals "No Signal"
*   **Symptom**: NHL Totals bets show 0 Sharp Score/Ticket/Money % despite data availability.
*   **Cause**: `pipeline/stages/process.py` (V2 Block) bypassed standard `markets.py` logic and hardcoded defaults.
*   **Fix**: Patched `process.py` to inject `get_nhl_sharp_data_helper` and manual sharp data lookup (Jan 2026).
*   **Ref**: Fix Verification Protocol Phase 7.

#### NBA Duplicate Bets (Double-Booking)
*   **Symptom**: Dashboard shows two bets for the same NBA game (often conflicting).
*   **Cause**: `processing/markets.py` Generic Moneyline block (Lines 1338+) lacked an exclusion for NBA, running alongside the V2 Phase 7 block.
*   **Fix**: Added explicit Firewall (`if sport == 'NBA': continue`) to the generic block.
*   **Ref**: `analysis_nba_model.md` (Jan 2026).

#### NCAAB "Missing Profile" / Bad Data
*   **Symptom**: Major teams (e.g., "Duke", "Iowa") have 0-diff features or default average stats.
*   **Cause**: 
    1.  **Normalization**: Mismatch between Short Name ("Duke") and Full Name ("Duke Blue Devils").
    2.  **Containment Bug**: "Iowa" matching "Iowa State" via unsafe `in` check.
*   **Fix**: Implemented Robust Matching Strategy (Exact -> Startswith -> Fuzzy) in `ncaab_h1_features.py` and `markets.py`.
*   **Ref**: Fix Verification Protocol Phase 8.

#### Database Persistence Crash (Json/NaN)
*   **Symptom**: Pipeline runs but no data persists; Logs show `invalid input syntax for type json`.
*   **Cause**: `NaN` values in Python dictionaries (from Models) cannot be serialized to JSON for Postgres.
*   **Fix**: Implemented `safe_json_serializer` in `persist.py` to convert `NaN` -> `null`.

---

## 5. Knowledge Gaps
1.  **Settlement vs Ingest**: Why two separate jobs? Overlap in functionality is ambiguous.
2.  **Systemd details**: `ops/systemd/` exists but isn't in the main `deploy_cron.sh`. How are these deployed?
3.  **(RESOLVED) Model Versioning (NHL V2)**: V2 is a hybrid execution.
    -   **Prediction**: `utils/models/nhl_totals_v2.py` (ElasticNet).
    -   **Orchestration**: `pipeline/stages/process.py`.
    -   **Sharp Data**: Manually injected via helper in `process.py`.

