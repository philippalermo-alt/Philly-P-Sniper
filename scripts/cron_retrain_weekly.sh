#!/usr/bin/env bash
set -euo pipefail

# Weekly NBA Retraining Wrapper
# Schedule: 0 11 * * 1

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_FILE="/home/ubuntu/cron_retrain.log"

# Explicitly set working directory
cd "$PROJECT_DIR"

echo "[$(date)] Starting Weekly Retrain..." >> "$LOG_FILE"

# Execute
/usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/retrain_nba_weekly.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date)] Finished Weekly Retrain (Exit: $EXIT_CODE)" >> "$LOG_FILE"
exit $EXIT_CODE
