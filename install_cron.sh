#!/bin/bash
# Install cron jobs for Philly P Sniper

# Define the cron jobs
# 1. Backfill at 09:00 AM UTC
JOB1="0 9 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 backfill_metrics.py >> /home/ubuntu/backfill.log 2>&1"

# 2. Train Model at 09:30 AM UTC
JOB2="30 9 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 -m models.train_v2 >> /home/ubuntu/train.log 2>&1"

# 3. Model Scans (8am, 12pm, 4pm ET -> 13:00, 17:00, 21:00 UTC)
JOB_SCAN_1="0 13 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 hard_rock_model.py >> /home/ubuntu/scan.log 2>&1"
JOB_SCAN_2="0 17 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 hard_rock_model.py >> /home/ubuntu/scan.log 2>&1"
JOB_SCAN_3="0 21 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 hard_rock_model.py >> /home/ubuntu/scan.log 2>&1"

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

# Add Model Scans (Dedup logic: check for hard_rock_model.py and the specific hour)
if grep -q "hard_rock_model.py" cur_cron; then
    echo "⚠️ Model Scan jobs already exist (simple check). Skipping updates to avoid duplicates."
else
    echo "$JOB_SCAN_1" >> cur_cron
    echo "$JOB_SCAN_2" >> cur_cron
    echo "$JOB_SCAN_3" >> cur_cron
    echo "✅ Added 3 Daily Model Scan jobs."
fi

crontab cur_cron
rm cur_cron

echo "✅ Cron jobs installed successfully."
crontab -l
