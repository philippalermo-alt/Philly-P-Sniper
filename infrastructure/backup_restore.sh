#!/bin/bash

# ==============================================================================
# 🛡️ PhillyEdge.AI Disaster Recovery & Backup Utility
# ==============================================================================
# Usage: 
#   ./infrastructure/backup_restore.sh --backup   (Create a full system snapshot)
#   ./infrastructure/backup_restore.sh --restore  (Restore from a snapshot)
# ==============================================================================

set -e

# Configuration
PROJECT_ROOT="/Users/purdue2k5/Documents/Philly-P-Sniper"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
SNAPSHOT_NAME="philly_edge_snapshot_${TIMESTAMP}"
SNAPSHOT_DIR="${BACKUP_DIR}/${SNAPSHOT_NAME}"

# AWS Connection Details
AWS_HOST="100.48.72.44"
AWS_USER="ubuntu"
AWS_KEY="${PROJECT_ROOT}/secrets/philly_key.pem"
REMOTE_DB_CONTAINER="philly_p_db"
REMOTE_DB_USER="user"

# Ensure backup directory exists
mkdir -p "${SNAPSHOT_DIR}"

log() {
    echo "project-log: [$(date +'%H:%M:%S')] $1"
}

# ==============================================================================
# 1. BACKUP ROUTINE
# ==============================================================================
run_backup() {
    log "🚀 Starting Full System Backup: ${SNAPSHOT_NAME}"

    # --- Step 1: Secure Configuration Files ---
    log "🔒 Securing sensitive configuration..."
    cp "${PROJECT_ROOT}/.env" "${SNAPSHOT_DIR}/.env.backup"
    cp "${PROJECT_ROOT}/secrets/philly_key.pem" "${SNAPSHOT_DIR}/philly_key.pem.backup"
    
    # --- Step 2: Database Dump (Remote -> Local) ---
    log "💾 Streaming Database Dump from AWS (${AWS_HOST})..."
    ssh -i "${AWS_KEY}" "${AWS_USER}@${AWS_HOST}" \
        "sudo docker exec ${REMOTE_DB_CONTAINER} pg_dump -U ${REMOTE_DB_USER} philly_sniper" \
        > "${SNAPSHOT_DIR}/database_full.sql"
    # echo "⚠️ SKIPPING DB DUMP (Temporary Fix for Exit 128)" > "${SNAPSHOT_DIR}/database_full.sql"
    
    if [ -s "${SNAPSHOT_DIR}/database_full.sql" ]; then
        log "✅ Database backup successful ($(du -h "${SNAPSHOT_DIR}/database_full.sql" | cut -f1))"
    else
        log "❌ ALLERT: Database backup failed or is empty!"
        exit 1
    fi

    # --- Step 3: Local Codebase Archive ---
    log "📦 Archiving Local Codebase (excluding artifacts)..."
    tar --exclude='node_modules' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='backups' \
        --exclude='.next' \
        --exclude='.DS_Store' \
        -czf "${SNAPSHOT_DIR}/codebase_archive.tar.gz" \
        -C "${PROJECT_ROOT}" .

    log "✅ Codebase archive created."

    # --- Step 4: Finalize Bundle ---
    log "🎁 Finalizing Restoration Kit..."
    cd "${BACKUP_DIR}"
    tar -czf "${SNAPSHOT_NAME}.tar.gz" "${SNAPSHOT_NAME}"
    rm -rf "${SNAPSHOT_NAME}" # Cleanup uncompressed directory

    log "✅ BACKUP COMPLETE: ${BACKUP_DIR}/${SNAPSHOT_NAME}.tar.gz"
    log "👉 To restore, use: ./infrastructure/backup_restore.sh --restore <file>"
}

# ==============================================================================
# 2. RESTORE ROUTINE
# ==============================================================================
run_restore() {
    echo "⚠️  RESTORATION MODE"
    echo "This is a destructive operation. It will overwrite local config and could overwrite the database."
    echo "Manual intervention is recommended for database restoration to prevent accidental data loss."
    echo ""
    echo "Instructions:"
    echo "1. Unzip the restoration kit."
    echo "2. Copy .env.backup to .env"
    echo "3. Use 'psql' to import database_full.sql"
    echo "4. Unzip codebase_archive.tar.gz to restore files."
}

# ==============================================================================
# Main Execution
# ==============================================================================

if [ "$1" == "--backup" ]; then
    run_backup
elif [ "$1" == "--restore" ]; then
    run_restore
else
    echo "Usage: $0 {--backup|--restore}"
    exit 1
fi
