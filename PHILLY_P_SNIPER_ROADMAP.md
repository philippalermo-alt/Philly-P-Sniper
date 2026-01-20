# 🦅 Philly P Sniper: Strategic Evolution Roadmap
**Date:** January 19, 2026
**Current Version:** v275 (Stabilized Dashboard, Basic Props, Soccer V1)

## Executive Summary
This document outlines the strategic path to evolve "Philly P Sniper" from a rule-based betting script into an institutional-grade algorithmic trading platform. The focus shifts from "finding +EV bets" to "predicting outcomes better than the market" using advanced data science and automation.

---

## 📅 Phase 1: Stabilization & CLV Tracking (1 Week)
**Goal:** Solidify trust in the current data and prove the edge exists mathematically.

### 1. Rigorous CLV Tracking (Critical)
*   **Why:** The only true predictor of long-term profit is beating the Closing Line Value (CLV).
*   **Action:**
    *   Store `closing_odds` for every bet (fetch 5 mins before kickoff).
    *   Build a "CLV Dashboard": Show clear charts of `(My Odds / Closing Odds) - 1`.
    *   **Success Metric:** consistently beating the close by >1.5%.
*   **Cost:** $0 (Existing APIs).

### 2. Alert System Upgrade
*   **Why:** Good bets disappear in minutes. The dashboard requires manual refreshing.
*   **Action:**
    *   Implement **Telegram Bot** notifications (free, instant).
    *   Send "Sniper Alerts" only for Edge > 5% and Sharp Score > 60.
*   **Cost:** $0.

### 3. Error Budgeting
*   **Why:** Props are currently using a generic Poisson model which may be too simple.
*   **Action:**
    *   Manual review of "Lost" prop bets to see if model missed injuries or line changes.
    *   add `status` checks (e.g., confirmed starter) before betting props.

---

## 📅 Phase 2: Data Deep Dive & Feature Engineering (1 Month)
**Goal:** Ingest granular data to build "Proprietary Features" that the market ignores.

### 1. Advanced Data Ingestion
*   **Why:** We currently use "Average" stats. We need context (Defense vs Position, Rest Days, Referee bias).
*   **Action:**
    *   **NBA/NHL:** Scrape/API for "Defense vs Position" (DvP) efficiency.
    *   **Soccer:** Integrate xG (Expected Goals) instead of raw goals.
*   **Cost:** ~$30/mo (API-Football Premium or similar for xG).

### 2. Model "V2" (Logistic Regression)
*   **Why:** Hard-coded weights (e.g., "70% model, 30% market") are arbitrary.
*   **Action:**
    *   Train a Logistic Regression model on our `intelligence_log`.
    *   Let the data decide the weights: `Outcome ~ ImpliedProb + MyProb + SharpMoney% + TimeToKickoff`.
*   **Cost:** $0 (Local Python/Scikit-Learn).

### 3. Bankroll Scalability
*   **Why:** Kelly Criterion is volatile.
*   **Action:**
    *   Implement **Fractional Kelly** with dynamic sizing based on "Confidence Tier".
    *   Add "Drawdown Control": Stop trading if daily loss > 5%.

---

## 📅 Phase 3: Machine Learning & Automation (6 Months)
**Goal:** Move from "Descriptive Analytics" to "Predictive AI".

### 1. XGBoost / LightGBM Implementation
*   **Why:** These models capture non-linear relationships (e.g., "Star player + Back-to-back game = Fatigue").
*   **Action:**
    *   Build a training pipeline (Airflow or Prefect).
    *   Features: Rolling averages, Rest days, Travel distance, Line movement velocity.
    *   Train separate models for specific markets (e.g., "NBA Player Points Model").
*   **Cost:** ~$50-100/mo (DigitalOcean Droplet or larger Heroku Dyno for training).

### 2. "Sniper Bot" (Automated Execution)
*   **Why:** Beating the market to a line change requires sub-second execution.
*   **Action:**
    *   Connect to sportsbook APIs (where legal/possible) or use browser automation (selenium/playwright) for "One-Click" betting.
    *   **Risk:** Account limitations. Must mimic human behavior.

### 3. Database Migration
*   **Why:** `intelligence_log` will get slow with millions of rows (tick data).
*   **Action:**
    *   Migrate to **TimescaleDB** (Postgres extension for time-series).
    *   Store distinct "Tick Data" for odds movement analysis.

---

## 📅 Phase 4: Enterprise Scale (1 Year)
**Goal:** Institutional-grade platform potentially suitable for syndication or SaaS.

### 1. Multi-Book Arbitrage & Synthetic Markets
*   **Why:** Risk-free profit (Arb) and creating synthetic lines (e.g., converting Spreads to MLs) reveals hidden value.
*   **Action:**
    *   Real-time websocket feeds from 10+ books.
    *   Graph-based arb finder.
*   **Cost:** $500+/mo (Professional Odds Feeds like OddsJam/Sportradar Enterprise).

### 2. Computer Vision (Live Betting)
*   **Why:** Live streams have data before APIs (latency arbitrage).
*   **Action:**
    *   OCR on live video feeds to detect score changes 3-5 seconds before books update.
    *   *Extremely high technical difficulty and cost.*

### 3. User Mesh (SaaS)
*   **Why:** Monetize the intelligence.
*   **Action:**
    *   Multi-tenant login.
    *   Stripe integration for specific "Model Subscriptions".

## Summary of Costs & ROI

| Timeframe | Est. Monthly Cost | Primary Focus | Exp. ROI Driver |
| :--- | :--- | :--- | :--- |
| **1 Week** | $0 | Reliability | Preventing bad bets (Bugs) |
| **1 Month** | $30 | Data Quality | Better inputs = Better predictions |
| **6 Months** | $100 | ML & Speed | Capturing value before market adjusts |
| **1 Year** | $500+ | Infrastructure | Scaling volume & proprietary data |

## Immediate Recommendation (Tomorrow Morning)
Start **Phase 1, Step 1**: Ensure we are saving Closing Line Value (CLV). Without this, we are flying blind regarding the actual quality of our "Edge".
