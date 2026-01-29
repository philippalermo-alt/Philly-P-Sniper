
-- Update Player Table
ALTER TABLE public.nhl_player_game_logs 
ADD COLUMN IF NOT EXISTS ixg FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS pp_toi INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS pp_goals INT DEFAULT 0;

-- Create Goalie Table
CREATE TABLE IF NOT EXISTS public.nhl_goalie_game_logs (
    game_id VARCHAR(20) NOT NULL,
    team VARCHAR(10),
    opponent VARCHAR(10),
    goalie_id INT NOT NULL,
    goalie_name VARCHAR(100),
    game_date DATE,
    
    is_starter BOOLEAN DEFAULT FALSE,
    toi_seconds INT DEFAULT 0,
    shots_against INT DEFAULT 0,
    goals_against INT DEFAULT 0,
    saves INT DEFAULT 0,
    save_pct FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (game_id, goalie_id)
);

CREATE INDEX IF NOT EXISTS idx_nhl_goalie_team_date ON nhl_goalie_game_logs(team, game_date);
