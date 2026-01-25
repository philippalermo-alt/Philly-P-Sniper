#!/bin/bash
KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "🦅 RUNNING MANUAL SETTLEMENT..."

# Copy script just in case it's not in image yet (Temporary measure)
# scp -i $KEY manual_settle.py $USER@$HOST:~/Philly-P-Sniper/

ssh -i $KEY $USER@$HOST << 'EOF'
    # Ensure script is in the container (if mapped volume? No, likely copy)
    # We'll assume it's there or we cp it in
    # sudo docker cp ~/Philly-P-Sniper/manual_settle.py philly_p_api:/app/
    
    # Run it
    sudo docker exec philly_p_api python3 manual_settle.py
EOF

echo "✅ Settlement Triggered."
