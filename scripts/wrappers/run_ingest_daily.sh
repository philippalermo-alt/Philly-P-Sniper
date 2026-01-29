#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# 🛡️ Wrapper: Daily Outcome Ingestion
# ==============================================================================
# Contract: Production Cron Safety Contract (2026-01-26)
# Schedule: Daily 04:00 AM EST (09:00 UTC)

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
# scripts/ingest_nba_outcomes.py uses current date or specific args.
# Default no-args = yesterday's outcomes.
$PYTHON_EXEC scripts/ingest_nba_outcomes.py >> "${LOG_DIR}/ingest_execution.log" 2>&1

EXIT_CODE=$?

exit $EXIT_CODE
