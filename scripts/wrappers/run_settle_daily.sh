#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# 🛡️ Wrapper: Daily Settlement
# ==============================================================================
# Contract: Production Cron Safety Contract (2026-01-26)
# Schedule: Daily 08:30 AM (Pending)

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/settle_wrapper.log"
PYTHON_EXEC="/usr/bin/sudo /usr/bin/docker exec -i philly_p_api python3"

# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

echo "[$(date -u)] 🚀 START: Daily Settlement Wrapper" >> "$LOG_FILE"

# Lock Mechanism (Parity with ops_cron_settle.sh)
LOCK_FILE="/tmp/philly_settle.lock"
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date -u)] ⚠️ SKIPPED: Settlement is already running." >> "$LOG_FILE"; exit 1; }

# cd to Project Root
cd "$PROJECT_DIR" || {
    echo "[$(date -u)] ❌ ERROR: Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# Execute
# Note: Previous script referenced 'manual_settle.py'. Verify this logic.
if [ -f "manual_settle.py" ]; then
    echo "[$(date -u)] Executing manual_settle.py..." >> "$LOG_FILE"
    $PYTHON_EXEC manual_settle.py >> "${LOG_DIR}/settle_execution.log" 2>&1
else
    echo "[$(date -u)] ❌ ERROR: manual_settle.py not found in $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date -u)] ✅ SUCCESS: Settlement Finished" >> "$LOG_FILE"
else
    echo "[$(date -u)] ❌ FAILURE: Settlement Exit Code $EXIT_CODE" >> "$LOG_FILE"
fi

echo "[$(date -u)] 🏁 END" >> "$LOG_FILE"
exit $EXIT_CODE
