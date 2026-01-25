#!/bin/bash

# Remove existing UCL sentinel jobs
crontab -l | grep -v "sentinel_ucl" > cur_cron

# Add new Specific UCL jobs
# 1. 12:00 PM EST (17:00 UTC) - Catches 12:45 PM Games
JOB1="0 17 * * 2,3 cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 soccer_sentinel.py >> /home/ubuntu/sentinel_ucl.log 2>&1"

# 2. 2:30 PM EST (19:30 UTC) - Catches 3:00 PM Games
JOB2="30 19 * * 2,3 cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web python3 soccer_sentinel.py >> /home/ubuntu/sentinel_ucl.log 2>&1"

echo "$JOB1" >> cur_cron
echo "$JOB2" >> cur_cron

# Install
crontab cur_cron
rm cur_cron

echo "✅ Cron Updated: Sentinel runs at 17:00 UTC and 19:30 UTC on Tue/Wed."
crontab -l | grep sentinel_ucl
