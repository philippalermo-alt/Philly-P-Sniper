# 🦅 Sniper Command Center

Here are your quick-access shortcuts for managing the system.
**One-Time Setup** (Run this once to enable shortcuts permanently):
```bash
echo "source /Users/purdue2k5/Documents/Philly-P-Sniper/aliases.sh" >> ~/.zshrc 
# Optional: Auto-start in project folder
echo '[[ -d "/Users/purdue2k5/Documents/Philly-P-Sniper" ]] && cd "/Users/purdue2k5/Documents/Philly-P-Sniper"' >> ~/.zshrc
source ~/.zshrc
```

| Shortcut | What it Does |
| :--- | :--- |
| **`sniper`** | 🔑 **Login**: SSH directly into your AWS server. |
| **`run_sniper_aws`** | 🚀 **Run AWS Model**: Manually triggers the model on the Live Server immediately. |
| **`sniper_logs`** | 📜 **Live Logs**: Watch the real-time logs from the AWS server. |
| **`sniper_deploy`** | 🔄 **Deploy**: Pushes your local code to AWS and restarts the server. |
| **`deploy_stream`** | 🧪 **Deploy Streamlit Only**: Runs the isolated `deploy_streamlit_isolated.sh` script. |

---

### 📝 Manual Commands (If needed)

#### Check Cron Schedule
```bash
sniper "crontab -l"
```

#### Run Model Scan (and save to log)
```bash
sniper "cd Philly-P-Sniper && sudo docker-compose exec web python3 hard_rock_model.py | tee -a /home/ubuntu/scan.log"
```

#### Check Docker Containers
```bash
sniper "sudo docker-compose ps"
```

#### View specific log files
```bash
# Backfill Logs
sniper "cat backfill.log"

# Training Logs
sniper "cat train.log"

#### 🏀 Manual: NCAAB 1H Model
*Runs the 1st Half model immediately (usually runs at 4pm/6pm).*
```bash
run_ncaab_1h
```

#### ⚽ Manual: Soccer Model V6 (Current)
*Runs the "Final" Market-Aware model (V6), filtered for Soccer only.*
```bash
run_soccer_v6
```

#### 📜 Manual: Soccer Model V5.2 (Legacy)
*Runs the older V5.2 stats-only model.*
```bash
run_soccer_v5
```
```


#### ⚽ Soccer Props
*   `run_soccer_props` - Runs the **Soccer Player Props Model** (Goals, Shots). Logs valid edges to DB.
*   `run_soccer_props_diag` - **Diagnostic Mode**. Prints a report of top found edges to the console. No DB write.

**Full Command (Standalone):**
```bash
sudo docker-compose exec -T api python3 prop_sniper.py
```

#### 🔓 Manual: NCAAB 1H (High Volume / Lower Thresholds)
*Runs the 1st Half model accepting lower edges (3%+) and confidence (65).*

**Option 1: Alias (Recommended)**
```bash
run_ncaab_loose
```


**Option 2: Full Command**
```bash
sniper "cd Philly-P-Sniper && sudo docker-compose exec -T api env NCAAB_MIN_EDGE=0.03 NCAAB_MIN_CONF=65 python3 ncaab_h1_model/ncaab_h1_edge_finder.py"
```
