# 🦅 Sniper Command Center

Here are your quick-access shortcuts for managing the system.
**Note**: You must restart your terminal (or run `source ~/.zshrc`) for these to take effect.

| Shortcut | What it Does |
| :--- | :--- |
| **`sniper`** | 🔑 **Login**: SSH directly into your AWS server. |
| **`run_sniper`** | 🚀 **Run Model**: Manually triggers `hard_rock_model.py` to find bets immediately. |
| **`run_backfill`** | 📥 **Fetch Data**: Manually triggers `backfill_metrics.py` to update historical data. |
| **`run_training`** | 🧠 **Train Model**: Manually triggers `models.train_v2` to retrain the AI. |
| **`sniper_logs`** | 📜 **View Logs**: Watches the live output of your automated scans (`scan.log`). |
| **`sniper_deploy`** | 🔄 **Update App**: Pulls the latest code from GitHub and rebuilds the server. |

---

### 📝 Manual Commands (If needed)

#### Check Cron Schedule
```bash
sniper "crontab -l"
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
```
