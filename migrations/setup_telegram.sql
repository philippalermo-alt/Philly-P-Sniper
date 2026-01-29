CREATE TABLE IF NOT EXISTS telegram_alerts (
    bet_id TEXT PRIMARY KEY,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    run_id TEXT,
    payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_telegram_alerts_created_at ON telegram_alerts(created_at);
