#!/bin/bash

# NCAAB H1 Model - Complete Pipeline Runner
# This script runs the full pipeline: data collection -> training -> edge finding

echo "🏀 NCAAB First Half Model Pipeline"
echo "===================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please create a .env file with your ODDS_API_KEY"
    echo "Example: cp .env.example .env"
    exit 1
fi

# Step 1: Data Collection (skip if data exists and is recent)
if [ ! -f "data/team_h1_profiles.json" ]; then
    echo "1️⃣ Collecting data from ESPN (first time setup)..."
    python ncaab_h1_scraper.py
else
    # Check if data is older than 7 days
    if [ $(find data/team_h1_profiles.json -mtime +7) ]; then
        echo "1️⃣ Refreshing data (>7 days old)..."
        python ncaab_h1_scraper.py
    else
        echo "1️⃣ Data is fresh (skipping collection)"
    fi
fi

# Step 2: Model Training (skip if model exists)
if [ ! -f "models/h1_total_model.pkl" ]; then
    echo ""
    echo "2️⃣ Training prediction model..."
    python ncaab_h1_train.py
else
    echo ""
    echo "2️⃣ Model already trained (skipping)"
fi

# Step 3: Find Edges
echo ""
echo "3️⃣ Scanning for betting edges..."
python ncaab_h1_edge_finder.py

echo ""
echo "✅ Pipeline complete!"
