#!/usr/bin/env bash
set -euo pipefail

# Ops Wrapper for Hourly main.py Execution
# Handles locking and logging per user requirements.

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="/home/ubuntu/phillyedge/logs"
LOCK_FILE="/tmp/philly_main.lock"
DATE_SUFFIX=$(date +%Y-%m-%d_%H00)
LOG_FILE="$LOG_DIR/main_${DATE_SUFFIX}.log"

# Explicitly set working directory
cd "$PROJECT_DIR"

# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

# Lock Mechanism using flock
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date)] Skipped: Job is already running." >> "$LOG_FILE"; exit 1; }

echo "==================================================" >> "$LOG_FILE"
echo "[$(date)] Starting Hourly Scan (Ops Cron)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

# Execute inside container
# We use sudo because the user context for docker usually requires it.
/usr/bin/sudo /usr/bin/docker exec philly_p_api python3 main.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "" >> "$LOG_FILE"
echo "[$(date)] Finished with Exit Code: $EXIT_CODE" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"
exit $EXIT_CODE
