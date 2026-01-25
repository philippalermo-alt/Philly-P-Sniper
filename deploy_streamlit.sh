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

echo "🔄 Executing Remote Build & Deploy..."
ssh -i $KEY $USER@$HOST << 'EOF'
    set -e
    cd ~/Philly-P-Sniper

    echo "🛑 Stopping running containers (Next.js or Streamlit)..."
    # Stop Next.js client if running
    sudo docker stop philly_p_client || true
    sudo docker rm philly_p_client || true
    # Stop Streamlit client if running
    sudo docker stop philly-client || true
    sudo docker rm philly-client || true

    echo "🏗️ Building Streamlit Image..."
    # Build from root Dockerfile
    sudo docker build -t philly-streamlit:latest .

    echo "🚀 Starting Streamlit..."
    # Map 3000 -> 8501 so user sees same URL
    # Connects to default network to reach Postgres at 'philly_p_db'
    sudo docker run -d \
        -p 3000:8501 \
        --name philly-client \
        --restart unless-stopped \
        --network philly-p-sniper_default \
        -e DATABASE_URL=postgresql://user:password@philly_p_db:5432/philly_sniper \
        philly-streamlit:latest

    echo "✅ Streamlit Deployment Complete."
EOF
