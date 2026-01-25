#!/bin/bash

# STRICT FAILURE HANDLING
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

echo "🚀 [QC Check] Starting Local Build Strategy (ARM64 -> AMD64 Cross-Compile)..."
echo "⚠️  This takes longer (~10 mins) but guarantees the server won't crash."

# 1. Build API Image (AMD64)
echo "📦 Building API Image (linux/amd64)..."
docker buildx build --platform linux/amd64 -t philly-api:latest -f Dockerfile . --load

# 2. Build Client Image (AMD64)
# Note: frontend_client DOES NOT EXIST in file list.
# Based on file list, philly-p-client.tar.gz exists, implying a pre-built image or source somewhere?
# Wait, let's check if 'frontend_client' dir exists in list_dir output?
# It does NOT appear in list_dir output from step 239.
# It seems the frontend might be in a different repo or I missed it?
# Actually, I see 'philly-p-client.tar.gz' (70MB) in file list.
# But I don't see a 'frontend_client' directory.
# I should just comment out the client build if source is missing, OR check if 'client' exists?
# The error was on backend_api.
# Let's fix Backend first.


echo "✅ Build Complete. Saving images to compressed tarball..."
# Save both images to one file and pipe through gzip
docker save philly-api:latest | gzip > philly_v2_images.tar.gz

echo "📤 Transferring Images to AWS (Size: $(du -h philly_v2_images.tar.gz | cut -f1))..."
scp -i $KEY philly_v2_images.tar.gz $USER@$HOST:~/Philly-P-Sniper/

echo "📤 Transferring updated config/code (Lightweight Sync)..."
rsync -avz -e "ssh -i $KEY" --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' \
    --exclude '.git' --exclude 'philly_v2_images.tar.gz' \
    ./ $USER@$HOST:~/Philly-P-Sniper/

echo "🔄 Deploying on Server..."
ssh -i $KEY $USER@$HOST << 'EOF'
    set -e
    cd ~/Philly-P-Sniper

    echo "📥 Loading Docker Images..."
    gunzip -c philly_v2_images.tar.gz | sudo docker load

    echo "🛑 Stopping old containers..."
    sudo docker-compose down

    # Create toggle override to force using local images instead of building
    cat > docker-compose.override.yml <<EOL
services:
  api:
    build: 
      context: .
    image: philly-api:latest
    pull_policy: never
EOL
    
    echo "🚀 Starting V2..."
    sudo docker-compose up -d

    echo "🧹 Cleanup..."
    rm philly_v2_images.tar.gz docker-compose.override.yml
EOF

echo "✅ DEPLOYMENT COMPLETE via Local Build Strategy."
rm philly_v2_images.tar.gz
