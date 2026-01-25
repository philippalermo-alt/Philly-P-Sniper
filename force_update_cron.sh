
crontab -l | grep -v "hard_rock_model.py" > clean_cron
echo "0 13 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web sh -c 'python3 hard_rock_model.py && python3 tweet_picks.py' >> /home/ubuntu/scan.log 2>&1" >> clean_cron
echo "0 17 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web sh -c 'python3 hard_rock_model.py && python3 tweet_picks.py' >> /home/ubuntu/scan.log 2>&1" >> clean_cron
echo "0 21 * * * cd /home/ubuntu/Philly-P-Sniper && /usr/bin/sudo /usr/local/bin/docker-compose exec -T web sh -c 'python3 hard_rock_model.py && python3 tweet_picks.py' >> /home/ubuntu/scan.log 2>&1" >> clean_cron
crontab clean_cron
rm clean_cron
echo "✅ Cron Updated with Twitter Pipeline"
crontab -l | grep tweet_picks
