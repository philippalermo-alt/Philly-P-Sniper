#!/bin/bash

# Start Streamlit in the foreground (Manual Trigger Only mode)
echo "🚀 Starting Dashboard (No Scheduler)..."
# Check where dashboard.py is
if [ -f "web/dashboard.py" ]; then
    streamlit run web/dashboard.py --server.port=8501 --server.address=0.0.0.0
else
    streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0
fi
