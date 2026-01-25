#!/bin/bash
set -e

KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

# 🛡️ DISASTER RECOVERY: AUTO-BACKUP TRAP
echo "🛡️ Initiating Safety-Net Backup..."
./infrastructure/backup_restore.sh --backup
if [ $? -ne 0 ]; then
    echo "❌ Backup Failed! Aborting Deployment to protect server state."
    exit 1
fi

echo "🧪 [Pre-Flight] Verifying critical files..."
if [ ! -f "dashboard.py" ]; then
    echo "❌ Error: dashboard.py not found!"
    exit 1
fi

echo "📤 Syncing Streamlit code to AWS..."
# Exclude git and other artifacts, but sync the isolated root files
rsync -avz -e "ssh -i $KEY" \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude '*.tar.gz' \
    --exclude 'frontend_client' \
    --exclude 'backend_api' \
    --exclude 'run_output.txt' \
    ./ $USER@$HOST:~/Philly-P-Sniper/

echo "🔄 Executing Remote Build & Deploy (Streamlit Only)..."
ssh -i $KEY $USER@$HOST << 'EOF'
    set -e
    cd ~/Philly-P-Sniper

    echo "🛑 Stopping Streamlit container..."
    # Only stop the streamlit container
    sudo docker stop philly-client || true
    sudo docker rm philly-client || true

    echo "🏗️ Building Streamlit Image..."
    sudo docker build -t philly-streamlit:latest .

    echo "🚀 Starting Streamlit..."
    # Run isolated, attached to the common network for DB access
    sudo docker run -d \
        -p 3000:8501 \
        --name philly-client \
        --restart unless-stopped \
        --network philly-p-sniper_default \
        -e DATABASE_URL=postgresql://user:password@philly_p_db:5432/philly_sniper \
        philly-streamlit:latest

    echo "✅ Streamlit Deployment Complete. Checking status..."
    sleep 5
    if sudo docker ps | grep -q philly-client; then
        echo "✅ Container is RUNNING."
    else
        echo "❌ Container failed to start. Checking logs..."
        sudo docker logs philly-client
        exit 1
    fi
EOF
