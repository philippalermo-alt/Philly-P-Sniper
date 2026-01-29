# 🦅 PhillyEdge.AI Sniper Shortcuts

*Current Version: v1.0.0-stable*

Here are the verified shortcuts for managing the system in the new refactored architecture.

## 🚀 Core Commands

| Action | Shortcut Command | What it Does |
| :--- | :--- | :--- |
| **Login** | `sniper` | SSH directly into your AWS server (`ubuntu@100.48.72.44`). |
| **Deploy** | `./deploy_aws.sh` | **Full Deployment**: Syncs code, rebuilds backend/database, and deploys frontend. |
| **Dashboard** | `./deploy_streamlit.sh` | **Rebuild**: Rebuilds/Redeploys Streamlit container (Slow). |
| **Fast Update** | `./hot_patch_dashboard.sh` | **Instant**: Hot-patches `dashboard.py` into running container (No downtime). |
| **Force Settle** | `./settle.sh` | **Grading**: Manually triggers settlement/grading of all pending bets. |
| **Run Scanner** | `python3 main.py` | **Local**: Runs the full betting pipeline (Fetch -> Enrich -> Process -> DB). |
| **Run Tests** | `./run_tests.sh` | **Verify**: Runs the full test suite and diagnostics. |

---

## ️ Remote Commands (Run after `sniper`)

Once logged into the server, use these commands:

### 🚀 Deployment & Operations
- **Deploy Cron Schedules** (Remote Only):
  ```bash
  ./scripts/deploy_cron.sh
  ```
- **Sync Code to Prod**:
  ```bash
  rsync -avz --exclude '.git' ./ ubuntu@<IP>:~/Philly-P-Sniper/
  ```

### 🏒 NHL Ops Loop (Manual)ly
Triggers the full pipeline immediately.
```bash
sudo docker exec philly_p_api python3 main.py
```

### 2. View Live Logs
Watch the backend orchestrator in real-time.
```bash
sudo docker logs -f philly_p_api
```

### 3. Check System Status
See if containers are healthy.
```bash
sudo docker-compose ps
```

---

## � Maintenance & Recovery

### Backup
Create a full system snapshot (Database + Code) in `backups/`.
```bash
./infrastructure/backup_restore.sh --backup
```

### Restore
Restore from a specific snapshot tarball.
```bash
./infrastructure/backup_restore.sh --restore <filename>
```
