#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# 🛡️ Wrapper: Daily Recap & Settlement
# ==============================================================================
# Contract: Production Cron Safety Contract (2026-01-26)
# Schedule: Daily 08:00 AM

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/recap_wrapper.log"
PYTHON_EXEC="/usr/bin/sudo /usr/bin/docker exec -i philly_p_api python3"

# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

echo "[$(date -u)] 🚀 START: Daily Recap Wrapper" >> "$LOG_FILE"

# cd to Project Root
cd "$PROJECT_DIR" || {
    echo "[$(date -u)] ❌ ERROR: Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Execute
echo "[$(date -u)] Executing scripts/daily_email_recap.py..." >> "$LOG_FILE"
# Note: daily_email_recap.py is in scripts/, so we call it from root.
$PYTHON_EXEC scripts/daily_email_recap.py >> "${LOG_DIR}/recap_execution.log" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -u)] ✅ SUCCESS: Recap Finished" >> "$LOG_FILE"
else
    echo "[$(date -u)] ❌ FAILURE: Recap Exit Code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "[$(date -u)] 🏁 END" >> "$LOG_FILE"
exit $EXIT_CODE
