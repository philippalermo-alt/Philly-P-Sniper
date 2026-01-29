#!/bin/bash
set -e

# Configuration
KEY="secrets/philly_key.pem"
HOST="ubuntu@100.48.72.44"
CONTAINER="philly-client"
LOCAL_DIR="web"
REMOTE_PATH="~/Philly-P-Sniper/web"
CONTAINER_PATH="/app/web"

echo "🔥 Initiating Hot-Patch for Dashboard..."

# 1. Sync local web/ directory to remote host
echo "📤 Syncing 'web/' directory to Host..."
rsync -avz -e "ssh -i $KEY" $LOCAL_DIR/ $HOST:$REMOTE_PATH/

# 2. Copy from Host into Running Container
echo "🐳 Injecting code into container ($CONTAINER)..."
ssh -i $KEY $HOST "sudo docker cp $REMOTE_PATH/. $CONTAINER:$CONTAINER_PATH/"

echo "✅ Hot-Patch Complete! Streamlit should auto-reload immediately."
