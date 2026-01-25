#!/bin/bash
KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "🚨 EMERGENCY KILL SWITCH ACTIVATED 🚨"
echo "Stopping all containers on $HOST..."

ssh -i $KEY $USER@$HOST << 'EOF'
    echo "Killing containers..."
    sudo docker stop $(sudo docker ps -q)
    echo "All containers stopped."
EOF

echo "✅ Kill Complete."
