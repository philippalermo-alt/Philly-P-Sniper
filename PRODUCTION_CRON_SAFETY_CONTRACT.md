# Production Cron Safety Contract

**Status**: ACTIVE & ENFORCED
**Effective Date**: 2026-01-26

This project operates under a strict **Cron Safety Contract**. All automated tasks must adhere to these rules to prevent production failures, permission drift, and environment issues.

## HARD RULES (Must Follow)

1. **Cron must NEVER execute Python files directly**
   * Cron may only call executable **shell wrapper scripts** (`.sh`).

2. **Every cron job must use a wrapper script** that:
   * Has a proper shebang (`#!/usr/bin/env bash`).
   * Uses `set -euo pipefail` (Strict Mode).
   * Activates the virtual environment explicitly (or executes within the Docker container context).
   * Uses absolute paths only (`/usr/bin/...`, `/home/ubuntu/...`).
   * Sets the working directory explicitly (`cd /path/to/project`).
   * Loads environment variables explicitly (if applicable).

3. **No cron job may rely on PATH, cwd, or implicit environment**
   * Assume the cron shell is empty and dumb.

4. **All cron commands must redirect logs**
   * Standard Output and Standard Error must be captured to a log file.

5. **All wrapper scripts must be executable (`chmod +x`)**
   * Permissions must be enforced during deployment.

## Mandatory Implementation Process

1. **Enumerate**: Identify the job function and schedule.
2. **Wrap**: Create a compliant shell script in `scripts/` (e.g., `scripts/cron_job_name.sh`).
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   
   # Configuration
   PROJECT_DIR="/home/ubuntu/Philly-P-Sniper"
   LOG_FILE="/home/ubuntu/cron_job_name.log"
   
   cd "$PROJECT_DIR"
   
   echo "[$(date)] Starting Job..." >> "$LOG_FILE"
   
   # Command (Absolute Paths)
   /usr/bin/sudo /usr/bin/docker-compose exec -T api python3 scripts/my_script.py >> "$LOG_FILE" 2>&1
   
   EXIT_CODE=$?
   echo "[$(date)] Finished (Exit: $EXIT_CODE)" >> "$LOG_FILE"
   exit $EXIT_CODE
   ```
3. **Deploy & Perms**: ensure the script is deployed and `chmod +x` is applied.
4. **Schedule**: Add to crontab with redundant logging redirect:
   ```
   0 12 * * * /home/ubuntu/Philly-P-Sniper/scripts/cron_job_name.sh >> /home/ubuntu/cron_errors.log 2>&1
   ```

## Enforcement

* **Refuse** to create or modify any cron job that does not follow this structure.
* If a cron job cannot be safely wrapped, **STOP** and explain why.
* **Audit** existing jobs periodically to ensure no regression.
