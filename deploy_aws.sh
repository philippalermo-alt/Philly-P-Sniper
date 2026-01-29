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

# Generate Immutable Tag
TAG=$(date +%Y%m%d%H%M%S)
echo "🏷️  Deployment Tag: $TAG"

# 1. Build API Image (AMD64)
echo "📦 Building API Image (linux/amd64)..."
docker buildx build --platform linux/amd64 -t philly-api:$TAG -f Dockerfile . --load

echo "✅ Build Complete. Saving images to compressed tarball..."
# Save image with immutable tag
docker save philly-api:$TAG | gzip > philly_v2_images.tar.gz

echo "📤 Transferring Images to AWS (Size: $(du -h philly_v2_images.tar.gz | cut -f1))..."
scp -i $KEY philly_v2_images.tar.gz $USER@$HOST:~/Philly-P-Sniper/

echo "📤 Transferring updated config/code (Lightweight Sync)..."
rsync -avz -e "ssh -i $KEY" --exclude 'node_modules' --exclude '.next' --exclude '__pycache__' \
    --exclude '.git' --exclude 'philly_v2_images.tar.gz' --exclude 'backups' \
    ./ $USER@$HOST:~/Philly-P-Sniper/

echo "🔄 Deploying on Server..."
ssh -i $KEY $USER@$HOST << EOF
    set -e
    cd ~/Philly-P-Sniper

    echo "📥 Loading Docker Images..."
    gunzip -c philly_v2_images.tar.gz | sudo docker load
    
    # Tag as latest for convenience on server (optional, or just use specific tag in compose)
    # But strictly, let's use the specific tag.
    
    echo "🛑 Stopping old containers..."
    sudo docker-compose down

    # Create toggle override to force using local images instead of building
    cat > docker-compose.override.yml <<EOL
services:
  api:
    image: philly-api:$TAG
    pull_policy: never
EOL
    
    echo "🚀 Starting V2..."
    sudo docker-compose up -d

    echo "🧹 Cleanup..."
    rm philly_v2_images.tar.gz docker-compose.override.yml
EOF

echo "✅ DEPLOYMENT COMPLETE via Local Build Strategy."
rm philly_v2_images.tar.gz
