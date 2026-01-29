#!/bin/bash
# ==============================================================================
# 🚀 PhillyEdge.AI Production Scheduler
# ==============================================================================
# Installs ALL production cron jobs.
# CRITICAL: Ensures Server Timezone is respected.

export TZ="America/New_York"
# 1. Pipeline Execution (Hourly)
# 2. Daily Recap (08:00 AM)
# 3. Backups (10:00 AM)

PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "$LOG_DIR"

# Paths
WRAPPER_DIR="${PROJECT_DIR}/scripts/wrappers"
PIPELINE_WRAPPER="${WRAPPER_DIR}/run_pipeline_hourly.sh"
RECAP_WRAPPER="${WRAPPER_DIR}/run_recap_daily.sh"
SETTLE_WRAPPER="${WRAPPER_DIR}/run_settle_daily.sh"
INGEST_WRAPPER="${WRAPPER_DIR}/run_ingest_daily.sh"
RETRAIN_WRAPPER="${WRAPPER_DIR}/run_retrain_weekly.sh"
BACKUP_SCRIPT="${PROJECT_DIR}/infrastructure/backup_restore.sh"

# Make Executable (Compliance Rule #5)
chmod +x "$PIPELINE_WRAPPER"
chmod +x "$RECAP_WRAPPER"
chmod +x "$SETTLE_WRAPPER"
chmod +x "$INGEST_WRAPPER"
chmod +x "$RETRAIN_WRAPPER"
chmod +x "$BACKUP_SCRIPT"

# Schedules (Times User-Defined Constraint 2026-01-27)

# 1. Pipeline: Hourly 9:00 AM to 9:00 PM EST (Server Time = EST)
PIPELINE_CMD="0 9-21 * * * ${PIPELINE_WRAPPER} >> ${LOG_DIR}/cron_pipeline.log 2>&1"

# 2. Ingest: Twice Daily (11:00 PM & 3:00 AM EST)
INGEST_CMD_1="0 23 * * * ${INGEST_WRAPPER} >> ${LOG_DIR}/cron_ingest.log 2>&1"
INGEST_CMD_2="0 3 * * * ${INGEST_WRAPPER} >> ${LOG_DIR}/cron_ingest.log 2>&1"

# 3. Settlement: Daily at 04:30 AM EST (Resolves bets from 3AM Ingest)
SETTLE_CMD="30 4 * * * ${SETTLE_WRAPPER} >> ${LOG_DIR}/cron_settle.log 2>&1"

# 4. Retrain: Weekly Mon at 06:00 AM EST (11:00 UTC)
RETRAIN_CMD="0 6 * * 1 ${RETRAIN_WRAPPER} >> ${LOG_DIR}/cron_retrain.log 2>&1"

# 5. Daily Recap: 07:00 AM EST (Reports on previous steps)
RECAP_CMD="0 7 * * * ${RECAP_WRAPPER} >> ${LOG_DIR}/cron_recap.log 2>&1"

# 6. Backup: Daily at 10:00 AM EST
BACKUP_CMD="0 10 * * * cd ${PROJECT_DIR} && ${BACKUP_SCRIPT} --backup >> ${PROJECT_DIR}/backups/automation.log 2>&1"

echo "🚀 Installing Production Schedule..."

# Generate Crontab Content
echo "DEBUG_PIPELINE: $PIPELINE_CMD"
cat << EOF > mycron
# PhillyEdge.AI Production Schedule
# Installed: $(date)

# 1. Betting Intelligence Pipeline (Hourly 9AM-9PM)
$PIPELINE_CMD

# 2. Ingest Outcomes (11PM & 3AM)
$INGEST_CMD_1
$INGEST_CMD_2

# 3. Settlement (04:30 AM)
$SETTLE_CMD

# 4. Weekly Retraining (Mon 06:00 AM)
$RETRAIN_CMD

# 5. Daily Recap (07:00 AM)
$RECAP_CMD

# 6. Disaster Recovery Backup (REMOVED per User Request)
# BACKUP_CMD removed.

EOF

# Install
crontab mycron
rm mycron

echo "✅ Schedule Installed Successfully:"
crontab -l
