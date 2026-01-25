# Scraping Operations Guide: Hybrid Backfill Architecture

## Overview
This document details the **verified** process for scraping complex data (Understat, etc.) that requires browser automation. We use a **Hybrid Architecture** where the heavy scraping happens **locally** (on the Mac) and the data is written **remotely** (to AWS Postgres) via an encrypted tunnel.

### Why this method?
1.  **Anti-Bot Protection**: Sites like Understat often block `requests` or headless server IPs. Local browsers (Chrome on Mac) pass these checks easily.
2.  **Resource Management**: Running headless Chrome on a small AWS instance is slow, unstable, and prone to crashing due to memory limits.
3.  **Stability**: Local execution leverages the Mac's stability and existing WebDriver setup, while the SSH tunnel ensures data is safely stored in production.

---

## 🚀 Running the Backfill (Step-by-Step)

### 1. Establish the SSH Tunnel
Map the remote database port (5432) to a local port (5433) securely.
```bash
# Run in a separate terminal tab
ssh -i secrets/philly_key.pem -L 5433:localhost:5433 -N ubuntu@100.48.72.44
```
*   `-L 5433:localhost:5433`: Forwards local port 5433 to the remote server's 5433 (which maps to Docker db:5432).
*   `-N`: No remote command (just forwards ports).

### 2. Configure Local Environment
Ensure your local `.env` file points to this tunneled port.
**File:** `.env`
```ini
# Tunneled Connection
DATABASE_URL=postgresql://user:password@localhost:5433/philly_sniper
```

### 3. Execute the Scraper
Run the backfill script. It will now scrape locally using your visible/headless Chrome and write results instantly to AWS.
```bash
# Run for specific league/season
python3 backfill_history.py --league EPL --season 2023

# OR Run the Full Batch (All 5 Leagues, 2023-2024)
python3 backfill_history.py
```

### 4. Monitor
*   **Local Termina**: Shows scraping logs (`INFO:UnderstatClient:Navigating...`)
*   **Remote Verification**: 
    ```bash
    ssh -i secrets/philly_key.pem ubuntu@100.48.72.44 "cd ~/Philly-P-Sniper && sudo docker-compose output db"
    ```

---

## 🛠️ Troubleshooting

### "Connection Refused" (Port 5433)
*   **Cause**: The SSH tunnel is not running or died.
*   **Fix**: Check if the `ssh -L` command is active. If `lsof -i :5433` matches nothing, restart the tunnel.

### "WebDriver Error" / "Chrome not reachable"
*   **Cause**: Local Chrome version updated, mismatch with Driver.
*   **Fix**: The script uses `webdriver-manager` so it should auto-fix. If not:
    ```bash
    rm -rf ~/.wdm
    pip3 install --upgrade webdriver-manager selenium
    ```

### "Missing 'matches' Table"
*   **Cause**: Database schema was reset or not initialized.
*   **Fix**: Run `from database import init_db; init_db()` in a Python shell connected to the DB.

---

## 📜 Critical Rules
1.  **Always Prefer Local + Tunnel for Heavy Scraping**: Do not install heavy GUI deps (Chromium/X11) on the production server unless absolutely necessary.
2.  **Document Success**: If a new scraping method works (e.g., finding a new JSON variable), update the regex/logic in `understat_client.py` and document it here immediately.
