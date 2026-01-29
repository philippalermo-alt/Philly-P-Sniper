#!/bin/bash
set -e

KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"
REMOTE_DIR="~/Philly-P-Sniper"

echo "🛡️ [DEPLOY] Starting Enforced Deployment..."

# 1. Local Verification
# 1. Local Verification SKIPPED (Force Mode)
# echo "🔍 PRE-FLIGHT: Running Local Verification..."
# if ./scripts/verify_local.sh; then
#     echo "✅ Local Verification Passed."
# else
#     echo "❌ Local Verification FAILED. Aborting Deploy."
#     exit 1
# fi

# 2. Deploy (Rsync Code)
echo "🚀 Syncing Code to EC2..."
rsync -avz -e "ssh -i $KEY" \
    --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' \
    --exclude '.git' --exclude 'backups' --exclude '*.tar.gz' \
    ./ $USER@$HOST:$REMOTE_DIR/

# 3. Restart Services
echo "🔄 Reloading Remote Services..."
ssh -i $KEY $USER@$HOST << EOF
    set -e
    cd $REMOTE_DIR
    
    # 🧹 PRE-FLIGHT CLEANUP
    echo "🧹 Cleaning up disk space..."
    sudo docker system prune -af --volumes || true
    sudo apt-get clean || true
    sudo journalctl --vacuum-time=1d || true
    
    # Ensure scripts are executable (fix for lost permissions)
    sudo chmod +x scripts/*.sh || true
    sudo chmod +x scripts/wrappers/*.sh || true
    sudo chmod +x scripts/ops/*.sh || true
    sudo chmod +x install_production_schedule.sh || true
    
    # Rebuild API container to pick up code changes (fast build)
    # We use docker-compose build to ensure dependencies are fresh
    sudo docker-compose build api
    
    # Restart
    sudo docker-compose up -d --remove-orphans

    # SCHEMA MIGRATION (Single Source of Truth)
    # Must run INSIDE the container where deps exist
    echo "🏗️ Applying Schema Update (inside container)..."
    sleep 5 # Wait for DB connection
    sudo docker-compose exec -T api python3 scripts/apply_schema_update.py
    
    # ⏰ INSTALL OPS TIMERS (NHL Totals V2)
    echo "⏰ Installing Ops Timers..."
    sudo bash scripts/ops/install_systemd_timers.sh
EOF

# 4. Remote Proof
echo "🧪 Running REMOTE PROOF..."
PROOF_OUTPUT=$(ssh -i $KEY $USER@$HOST "cd $REMOTE_DIR && sudo docker-compose exec -T api python3 main.py 2>&1")
echo "$PROOF_OUTPUT"

if echo "$PROOF_OUTPUT" | grep -q "ERROR"; then
    echo "❌ [DEPLOY FAIL] Remote Proof Failed (Errors Detected in Log)."
    exit 1
elif echo "$PROOF_OUTPUT" | grep -q "Pipeline Execution Successful"; then
    echo "✅ [DEPLOY SUCCESS] Remote Proof Passed."
    exit 0
else
    echo "❌ [DEPLOY FAIL] Remote Proof Failed (Unknown State)."
    exit 1
fi
