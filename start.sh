#!/bin/bash

# Start Streamlit in the foreground (Manual Trigger Only mode)
echo "🚀 Starting Dashboard (No Scheduler)..."
streamlit run dashboard.py --server.port=8501 --server.address=0.0.0.0
