#!/bin/bash
KEY="secrets/philly_key.pem"
HOST="100.48.72.44"
USER="ubuntu"

echo "🔎 Checking for rogue processes..."
ssh -i $KEY $USER@$HOST << 'EOF'
    echo "--- DOCKER CONTAINERS ---"
    sudo docker ps -a
    
    echo "--- PYTHON PROCESSES ---"
    ps aux | grep python
    
    echo "--- KILLING ALL PYTHON & DOCKER ---"
    sudo docker stop $(sudo docker ps -q) 2>/dev/null
    sudo pkill -f python
    sudo pkill -f streamlit
EOF
