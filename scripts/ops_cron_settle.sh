#!/bin/bash
# Ops Wrapper for Settle Wagers Execution
# Handles locking and logging.

LOG_DIR="/home/ubuntu/phillyedge/logs"
DATE_SUFFIX=$(date +%Y-%m-%d_%H%M)
LOG_FILE="$LOG_DIR/settle_${DATE_SUFFIX}.log"
LOCK_FILE="/tmp/philly_settle.lock"

# Ensure Log Dir Exists
mkdir -p "$LOG_DIR"

# Lock Mechanism
exec 200>"$LOCK_FILE"
flock -n 200 || { echo "[$(date)] Skipped: Settle Job is already running." >> "$LOG_FILE"; exit 1; }

echo "==================================================" >> "$LOG_FILE"
echo "[$(date)] Starting Settle Wagers (Ops Cron)" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"

# Execute inside container
# User specified command: sudo docker exec philly_p_api python3 scripts/settle_wagers.py
# CORRECTION: User clarified to use existing logic: python3 manual_settle.py (in root)
# The file manual_settle.py is expected to be in /app inside the container.
sudo docker exec philly_p_api python3 manual_settle.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "" >> "$LOG_FILE"
echo "[$(date)] Finished with Exit Code: $EXIT_CODE" >> "$LOG_FILE"
echo "==================================================" >> "$LOG_FILE"
