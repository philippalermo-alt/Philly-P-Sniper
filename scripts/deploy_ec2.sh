#!/bin/bash
set -e

KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"
REMOTE_DIR="~/Philly-P-Sniper"

echo "🛡️ [DEPLOY] Starting Enforced Deployment..."

# 1. Local Verification
echo "🔍 PRE-FLIGHT: Running Local Verification..."
if ./scripts/verify_local.sh; then
    echo "✅ Local Verification Passed."
else
    echo "❌ Local Verification FAILED. Aborting Deploy."
    exit 1
fi

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
    
    # Rebuild API container to pick up code changes (fast build)
    # We use docker-compose build to ensure dependencies are fresh
    sudo docker-compose build api
    
    # Restart
    sudo docker-compose up -d --remove-orphans

    # Deploy Cron Schedules
    echo "⏰ Updating Cron Jobs..."
    bash scripts/deploy_cron.sh
EOF

# 4. Remote Proof
echo "🧪 Running REMOTE PROOF..."
if ssh -i $KEY $USER@$HOST "cd $REMOTE_DIR && sudo docker-compose exec -T api python3 main.py"; then
    echo "✅ [DEPLOY SUCCESS] Remote Proof Passed."
    exit 0
else
    echo "❌ [DEPLOY FAIL] Remote Proof Failed."
    exit 1
fi
