-- Add Phase 2 Metrics columns to intelligence_log table
ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_xg REAL;
ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_xg REAL;
ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS dvp_rank REAL;
ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_adj_em REAL;
ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_adj_em REAL;
