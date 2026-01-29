# Quick Reference Guide & Troubleshooting Vault

## 🚨 Critical Protocols

### Fix Verification Protocol (Rule 166)
**MANDATORY 4-PHASE PROCESS**:
1.  **Diagnose**: Identify root cause (Local vs Prod).
2.  **Fix**: Implement solution (Migration Script).
3.  **Test**: Verify locally.
4.  **Document**: Update this guide.

---

### NHL Pipeline (Philly-P-Sniper)
**Frozen Pipeline (Phases 1-4)**:
1.  **SOG**: `python3 scripts/train_sog_model_nb.py`
2.  **Goals**: `python3 scripts/train_goals_model.py`
3.  **Assists**: `python3 scripts/train_assists_model_nb.py`
4.  **Points**: `python3 scripts/build_points_sim.py`

**Production Workflow (Phase 5/6 - Daily)**:
1.  **Update DB**: `python3 scripts/ingest_nhl_history_safe.py`
2.  **Generate Projections**: `python3 scripts/generate_daily_projections.py`
    - *Output*: `data/nhl_processed/daily_projections.csv`
3.  **Run Rec Engine**: `python3 scripts/nhl_recommendation_engine.py`
    - *Action*: Logs +EV bets w/ Gates to Dashboard.
    - *Audit*: `data/nhl_processed/candidates_audit.csv`

**Data Operations**:
- **Ingest Goalies**: `python3 scripts/ingest_nhl_goalies.py` (Daily)
- **Ingest PP**: `python3 scripts/ingest_nhl_pp.py` (Daily)

---
### Database & Infrastructure Synchronization

### ⚠️ Core Concept: Dual-Environment State
The Dashboard on EC2 reads from the **Production Database** (Docker `db` container), while your local code reads from `localhost`.
**CRITICAL RULE**: To remove an entry from the live Dashboard, you must delete it from **BOTH** the Local Database (dev) **AND** the Production Database (live).

### Protocol: Production Data Deletion
**NEVER** modify `main.py` to run one-off deletions. Use this process:

1.  **Script**: Create a specific cleanup script (e.g., `scripts/migrations/fix_dupes.py`).
2.  **Deploy**: Push the script to the server.
    *   Run `deploy_fast.sh`
3.  **Execute**: Run the script remotely inside the Production API container.
    ```bash
    ssh -i secrets/philly_key.pem ubuntu@<IP>
    cd Philly-P-Sniper
    sudo docker-compose exec api python3 scripts/migrations/fix_dupes.py
    ```
4.  **Verify**: Click "Refresh Data" on the Dashboard (cache cleared).

---

