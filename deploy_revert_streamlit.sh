#!/bin/bash
set -e

KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "📤 Syncing code to AWS..."
rsync -avz -e "ssh -i $KEY" \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude '*.tar.gz' \
    --exclude 'frontend_client' \
    ./ $USER@$HOST:~/Philly-P-Sniper/

echo "🔄 executing remote revert..."
ssh -i $KEY $USER@$HOST << 'EOF'
    set -e
    cd ~/Philly-P-Sniper

    echo "🛑 Stopping Next.js client..."
    sudo docker stop philly_p_client || true
    sudo docker rm philly_p_client || true
    # Also stop generic name if exists
    sudo docker stop philly-client || true
    sudo docker rm philly-client || true

    echo "🏗️ Building Streamlit Image..."
    # Build from root Dockerfile
    sudo docker build -t philly-streamlit:latest .

    echo "🚀 Starting Streamlit..."
    # Map 3000 -> 8501 so user sees same URL
    # Ensure it's on the same network as DB if needed. 
    # Usually docker-compose created 'philly-p-sniper_default' network.
    # We will try to attach to it or link specifically.
    # The existing DB container is 'philly_p_db'.
    
    sudo docker run -d \
        -p 3000:8501 \
        --name philly-client \
        --restart unless-stopped \
        --network philly-p-sniper_default \
        -e DATABASE_URL=postgresql://user:password@philly_p_db:5432/philly_sniper \
        philly-streamlit:latest

    echo "✅ Revert Complete."
EOF
