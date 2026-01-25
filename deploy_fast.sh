#!/bin/bash
set -e

KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "⚡ Starting FAST Deployment (Skipping Backup)..."

# 1. Build API Image (AMD64)
echo "📦 Building API Image (linux/amd64)..."
docker buildx build --platform linux/amd64 -t philly-api:latest -f Dockerfile . --load

echo "✅ Build Complete. Saving image..."
docker save philly-api:latest | gzip > philly_fresh.tar.gz

echo "📤 Transferring Image (Size: $(du -h philly_fresh.tar.gz | cut -f1))..."
scp -i $KEY philly_fresh.tar.gz $USER@$HOST:~/Philly-P-Sniper/

echo "📤 Syncing Code (Excluding Heavy Files)..."
# Exclude heavy artifacts to speed up rsync
rsync -avz -e "ssh -i $KEY" \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude '*.tar.gz' \
    --exclude '*.csv' \
    --exclude 'backups' \
    --exclude 'January 25 Disaster Recovery' \
    --exclude 'infrastructure' \
    ./ $USER@$HOST:~/Philly-P-Sniper/

echo "🔄 Reloading Server..."
ssh -i $KEY $USER@$HOST << 'EOF'
    set -e
    cd ~/Philly-P-Sniper

    echo "📥 Loading Docker Image..."
    gunzip -c philly_fresh.tar.gz | sudo docker load

    echo "🚀 Restarting API..."
    # Force recreation of API container
    cat > docker-compose.override.yml <<EOL
services:
  api:
    image: philly-api:latest
    pull_policy: never
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/philly_sniper
    command: sleep infinity
EOL
    
    sudo docker-compose up -d --remove-orphans
    
    rm philly_fresh.tar.gz docker-compose.override.yml
EOF

echo "✅ FAST DEPLOY COMPLETE."
rm philly_fresh.tar.gz
