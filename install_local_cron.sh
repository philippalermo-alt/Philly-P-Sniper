#!/bin/bash
# ==============================================================================
# 🛡️ PhillyEdge.AI Local Backup Scheduler
# ==============================================================================
# Installs a persistent daily cron job to back up the entire platform.

PROJECT_DIR="$(pwd)"
SCRIPT_PATH="${PROJECT_DIR}/infrastructure/backup_restore.sh"
LOG_FILE="${PROJECT_DIR}/backups/automation.log"

# Schedule: 10:00 AM Daily
CRON_CMD="0 10 * * * cd ${PROJECT_DIR} && ${SCRIPT_PATH} --backup >> ${LOG_FILE} 2>&1"

echo "🛡️ Installing Daily Disaster Recovery Schedule..."
echo "📂 Project: ${PROJECT_DIR}"
echo "📅 Schedule: Daily at 10:00 AM"

# Backup existing cron
crontab -l > mycron.backup 2>/dev/null

# Append new job if not exists
crontab -l 2>/dev/null > mycron
if grep -q "backup_restore.sh" mycron; then
    echo "⚠️  Backup job already exists. Skipping."
else
    echo "# PhillyEdge.AI Daily Backup" >> mycron
    echo "$CRON_CMD" >> mycron
    crontab mycron
    echo "✅ Success: Daily backup installed."
fi
rm mycron
