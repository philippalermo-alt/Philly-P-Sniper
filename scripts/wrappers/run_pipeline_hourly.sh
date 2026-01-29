#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# 🛡️ Wrapper: Hourly Betting Pipeline
# ==============================================================================
# Contract: Production Cron Safety Contract (2026-01-26)
# Schedule: Hourly

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/pipeline_wrapper.log"
PYTHON_EXEC="/usr/bin/sudo /usr/bin/docker exec -i philly_p_api python3"

# Force V2 Models ON for Hourly Runs
export NHL_TOTALS_V2_ENABLED=true
export ENABLE_NBA_V2=true
export SKIP_NHL=false


# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

echo "[$(date -u)] 🚀 START: Hourly Pipeline Wrapper" >> "$LOG_FILE"

# Lock Mechanism (Parity with ops_cron_main.sh)
LOCK_FILE="/tmp/philly_pipeline.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date -u)] ⚠️ SKIPPED: Pipeline is already running." >> "$LOG_FILE"; exit 1; }

# cd to Project Root
cd "$PROJECT_DIR" || {
    echo "[$(date -u)] ❌ ERROR: Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Execute
echo "[$(date -u)] Executing main.py..." >> "$LOG_FILE"
$PYTHON_EXEC main.py >> "${LOG_DIR}/pipeline_execution.log" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -u)] ✅ SUCCESS: Pipeline Finished" >> "$LOG_FILE"
else
    echo "[$(date -u)] ❌ FAILURE: Pipeline Exit Code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "[$(date -u)] 🏁 END" >> "$LOG_FILE"
exit $EXIT_CODE
