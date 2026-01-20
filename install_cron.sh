#!/bin/bash
# Install cron jobs for Philly P Sniper

# Define the cron jobs
# 1. Backfill at 09:00 AM UTC
JOB1="0 9 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 backfill_metrics.py >> /home/ubuntu/backfill.log 2>&1"

# 2. Train Model at 09:30 AM UTC
JOB2="30 9 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 -m models.train_v2 >> /home/ubuntu/train.log 2>&1"

# Check if jobs exist, else append
crontab -l 2>/dev/null > cur_cron

if grep -q "backfill_metrics.py" cur_cron; then
    echo "⚠️ Backfill job already exists. Skipping."
else
    echo "$JOB1" >> cur_cron
    echo "✅ Added Backfill job."
fi

if grep -q "models.train_v2" cur_cron; then
    echo "⚠️ Train job already exists. Skipping."
else
    echo "$JOB2" >> cur_cron
    echo "✅ Added Train job."
fi

crontab cur_cron
rm cur_cron

echo "✅ Cron jobs installed successfully."
crontab -l
