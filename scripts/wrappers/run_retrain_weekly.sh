#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# 🛡️ Wrapper: Weekly NBA Retraining
# ==============================================================================
# Contract: Production Cron Safety Contract (2026-01-26)
# Schedule: Weekly Mon 06:00 AM EST (11:00 UTC)

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="${PROJECT_DIR}/logs"
PYTHON_EXEC="/usr/bin/sudo /usr/bin/docker exec -i philly_p_api python3"

# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

# cd to Project Root
cd "$PROJECT_DIR" || {
    echo "[$(date -u)] ❌ ERROR: Failed to cd to $PROJECT_DIR" >> "${LOG_DIR}/cron_errors.log"
    exit 1
}

# Execute
$PYTHON_EXEC scripts/retrain_nba_weekly.py >> "${LOG_DIR}/retrain_execution.log" 2>&1

EXIT_CODE=$?

exit $EXIT_CODE
