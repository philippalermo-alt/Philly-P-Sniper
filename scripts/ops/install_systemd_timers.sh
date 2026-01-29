#!/bin/bash
# install_systemd_timers.sh
# Installs NHL Totals V2 Timers to Systemd on EC2

SYSTEMD_DIR="/etc/systemd/system"
# We expect to run this from the repo root or scripts/ops dir.
# Ideally we find the absolute path to ops/systemd
PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
REPO_SYSTEMD_DIR="${PROJECT_DIR}/ops/systemd"

echo "=== NHL Totals V2 Scheduler Installer ==="

# 1. Verify Units Exist
if [ ! -d "$REPO_SYSTEMD_DIR" ]; then
    echo "❌ Error: $REPO_SYSTEMD_DIR directory not found."
    exit 1
fi

# 2. Copy Units & Timers
echo "Copying units to $SYSTEMD_DIR..."
# Must run as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Error: Must run as root (use sudo)."
    exit 1
fi

cp "$REPO_SYSTEMD_DIR"/*.service "$SYSTEMD_DIR/"
cp "$REPO_SYSTEMD_DIR"/*.timer "$SYSTEMD_DIR/"

# 3. Reload & Enable
echo "Reloading Systemd Daemon..."
systemctl daemon-reload

echo "Enabling Timers..."
timers=(
    "nhl-odds-ingest.timer"
    "nhl-totals-run.timer"
    "nhl-totals-kpi.timer"
    "nhl-totals-retrain.timer"
    "nba-kpi.timer"
    "nba-retrain.timer"
)

for t in "${timers[@]}"; do
    if systemctl enable --now "$t"; then
        echo "✅ Enabled $t"
    else
        echo "❌ Failed to enable $t"
    fi
done

echo -e "\n=== Current Timers (NHL) ==="
systemctl list-timers --all | grep nhl- || echo "No NHL timers found."
