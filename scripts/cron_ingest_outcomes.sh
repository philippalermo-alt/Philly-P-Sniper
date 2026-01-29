#!/usr/bin/env bash
set -euo pipefail

# Daily Outcomes Ingestion Wrapper
# Schedule: 0 9 * * *

# Configuration
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_FILE="/home/ubuntu/cron_ingest.log"

# Explicitly set working directory
cd "$PROJECT_DIR"

echo "[$(date)] Starting Outcomes Ingestion..." >> "$LOG_FILE"

# Execute
/usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/ingest_nba_outcomes.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date)] Finished Outcomes Ingestion (Exit: $EXIT_CODE)" >> "$LOG_FILE"
exit $EXIT_CODE
