# Philly-P-Sniper Process Log

## 🚨 CRITICAL RULES
1. **DEPLOYMENT PERMISSION**: You MUST ask for explicit permission before running `deploy_aws` (or `sniper_deploy`). Changes do not take effect online until this command is run, but it triggers a full rebuild. **NEVER** run this without asking first.

## Process Notes
### Deployment
- Command: `/Users/purdue2k5/Documents/Philly-P-Sniper/deploy_aws.sh`
- Triggers: Docker Build -> Service Restart
- Verification: Check `sniper_logs` after deploy.

### Backfill
- Status: Running (started Jan 23)
- Logs: `backfill_full_run_optimized.log`

### Conflict Resolution
- Logic: "Last Bet Stands".
- Implementation: `probability_models.py` (US Sports & Soccer blocks).
- Mechanism: Before inserting, queries DB for `PENDING` bets on same Event+Market. If logic flips (e.g. Over -> Under), OLD bet is DELETED.

### NCAAB Modeling
- **Data Rule**: **CURRENT SEASON ONLY**. Do not train on historical seasons (roster turnover invalidates past data).
- **Training Frequency**: Retrain weekly to capture new team form.
