#!/bin/bash
KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "🦅 FORCE RUNNING PHYLLY P SNIPER ON REMOTE HOST..."

ssh -i $KEY $USER@$HOST << 'EOF'
    echo "inside host..."
    sudo docker exec philly_p_api python3 hard_rock_model.py
EOF

echo "✅ Trigger Complete."
