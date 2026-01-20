-- migrations/add_bet_type.sql
-- Add bet_type column to intelligence_log table
ALTER TABLE intelligence_log
ADD COLUMN bet_type VARCHAR(10) NOT NULL DEFAULT 'ml';

-- Backfill existing rows with appropriate bet_type based on market data if possible.
-- For simplicity, set default 'ml' for existing rows.
