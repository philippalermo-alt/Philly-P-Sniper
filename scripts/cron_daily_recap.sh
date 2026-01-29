#!/usr/bin/env bash
set -euo pipefail

# Daily Email Recap Wrapper
# Schedule: 0 12 * * *

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_FILE="/home/ubuntu/cron_recap.log"

# Explicitly set working directory
cd "$PROJECT_DIR"

echo "[$(date)] Starting Daily Recap..." >> "$LOG_FILE"

# Execute
/usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/daily_email_recap.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date)] Finished Daily Recap (Exit: $EXIT_CODE)" >> "$LOG_FILE"
exit $EXIT_CODE
