# Deploying to DigitalOcean (or any VPS)

This guide shows how to run "Philly P Sniper" on a $6/mo DigitalOcean Droplet using Docker. This avoids Heroku's complexity and variable costs.

## 1. Create a Droplet (Done)
- Server IP: `64.225.56.198`

## 2. Connect to the Server
Open your terminal (on your Mac) and run this exact command to force password login:
```bash
ssh -o PubkeyAuthentication=no root@64.225.56.198
```
*(Enter the password you set in the web console)*

## 3. Set Up the Application
Run these commands **on the server**:

### A. Clone the Repository
```bash
git clone https://github.com/philippalermo-alt/Philly-P-Sniper.git
cd Philly-P-Sniper
```

### B. Configure Environment Variables
Create the `.env` file with your real secrets:
```bash
nano .env
```
Paste your secrets in this format:
```text
# Database URL is NOT needed here (it is handled internally by Docker)
ODDS_API_KEY=your_odds_api_key
ACTION_NETWORK_API_KEY=your_key_if_needed
DASHBOARD_PASSWORD=your_secret_password
```
Press `Ctrl+X`, then `Y`, then `Enter` to save.

### C. Start the App
```bash
docker compose up -d --build
```
Your app is now live at `http://64.225.56.198:8501`.

## 4. Set Up the Scheduler (Cron Job)
1.  Open crontab:
    ```bash
    crontab -e
    ```
2.  Add this line to run the scraper every 15 mins:
    ```text
    */15 * * * * cd /root/Philly-P-Sniper && /usr/bin/docker compose run --rm web python hard_rock_model.py >> /var/log/sniper_cron.log 2>&1
    ```
3.  Save and exit.

## 5. Maintenance
- **View Logs**: `docker compose logs -f web`
- **Update Code**:
    ```bash
    git pull
    docker compose up -d --build
    ```
