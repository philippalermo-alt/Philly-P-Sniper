
-- Table: public.nhl_player_game_logs

CREATE TABLE IF NOT EXISTS public.nhl_player_game_logs (
    game_id VARCHAR(20) NOT NULL,
    player_id INT NOT NULL,
    player_name VARCHAR(100),
    team VARCHAR(10),
    opponent VARCHAR(10),
    game_date DATE,
    
    -- Stats
    goals INT DEFAULT 0,
    assists INT DEFAULT 0,
    points INT DEFAULT 0,
    shots INT DEFAULT 0,
    toi_seconds INT DEFAULT 0,
    pp_points INT DEFAULT 0,
    plus_minus INT DEFAULT 0,
    
    -- Metadata
    is_home BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Composite Key
    PRIMARY KEY (game_id, player_id)
);

-- Indexes for model querying (Rolling Windows)
CREATE INDEX IF NOT EXISTS idx_nhl_pgl_player_date ON nhl_player_game_logs(player_id, game_date ASC);
CREATE INDEX IF NOT EXISTS idx_nhl_pgl_team_date ON nhl_player_game_logs(team, game_date ASC);
CREATE INDEX IF NOT EXISTS idx_nhl_pgl_date ON nhl_player_game_logs(game_date);
