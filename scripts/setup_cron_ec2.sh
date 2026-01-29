#!/bin/bash
# Install Phase 8 Cron Jobs on EC2

# 1. Define Jobs
# 4:00 AM ET = 09:00 UTC (Daily Ingest)
JOB_INGEST="0 9 * * * cd ~/Philly-P-Sniper && /usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/ingest_nba_outcomes.py >> ~/cron_ingest.log 2>&1"

# 6:00 AM ET Mon = 11:00 UTC Mon (Weekly Retrain)
JOB_RETRAIN="0 11 * * 1 cd ~/Philly-P-Sniper && /usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/retrain_nba_weekly.py >> ~/cron_retrain.log 2>&1"

# 2. Add to Crontab (Idempotent-ish check)
(crontab -l 2>/dev/null | grep -v "ingest_nba_outcomes.py" | grep -v "retrain_nba_weekly.py"; echo "$JOB_INGEST"; echo "$JOB_RETRAIN") | crontab -

echo "✅ Phase 8 Cron Jobs Installed:"
crontab -l | grep "Philly-P-Sniper"
