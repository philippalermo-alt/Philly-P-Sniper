# NHL V2 Systemd Installation Proof

**Date**: 2026-01-27
**Target**: `ubuntu@100.48.72.44`
**Status**: 🟢 **INSTALLED & VERIFIED**

## 1. Unit Files Installed
Files synced to `/etc/systemd/system/`:
- `nhl-odds-ingest.service` / `.timer`
- `nhl-totals-run.service` / `.timer`
- `nhl-totals-kpi.service` / `.timer`
- `nhl-totals-retrain.service` / `.timer`

**Configuration**:
- User: `ubuntu`
- WorkDir: `/home/ubuntu/Philly-P-Sniper`
- Exec: `docker exec -i philly_p_api python3 ...` (Hardened, no sudo needed)
- Logs: `/home/ubuntu/Philly-P-Sniper/logs/systemd/*.log`

## 2. Timer Status
`systemctl list-timers --all | grep nhl-`
```
Tue 2026-01-27 19:00:00 UTC ... nhl-odds-ingest.timer
Wed 2026-01-28 03:00:00 UTC ... nhl-totals-run.timer
Wed 2026-01-28 04:00:00 UTC ... nhl-totals-kpi.timer
Mon 2026-02-02 05:00:00 UTC ... nhl-totals-retrain.timer
```

## 3. Manual Execution Proof
**Services Started**: `ingest`, `run`, `kpi`.
**Log Verification**: `logs/systemd/nhl-totals-run.log`

```
2026-01-27 13:47:32,910 [INFO] [PROOF] NHL_TOTALS_V2_ACTIVE model=ElasticNet sigma=2.242 bias=-0.1433 features=nhl_totals_features_v1
```
✅ **V2 Proof Marker Confirmed**

## 4. Operational Notes
- **Log Location**: `~/Philly-P-Sniper/logs/systemd/`
- **Environment**: Container `philly_p_api` (Docker Exec)
