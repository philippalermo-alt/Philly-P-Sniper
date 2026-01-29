from db.connection import get_db

def init_nba_schema():
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    cur = conn.cursor()
    try:
        # Table 1: Historical Games (Stats)
        # Primary Key: game_id (NBA Official)
        print("Creating Table: nba_historical_games...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nba_historical_games (
                game_id TEXT PRIMARY KEY,
                season_id TEXT,
                game_date TIMESTAMP,
                game_date_est TIMESTAMP, -- Normalized EST Date
                home_team_id TEXT,
                home_team_name TEXT,
                away_team_id TEXT,
                away_team_name TEXT,
                home_score INTEGER,
                away_score INTEGER,
                
                -- Four Factors (Advanced Stats)
                home_efg_pct REAL,
                away_efg_pct REAL,
                home_tov_pct REAL,
                away_tov_pct REAL,
                home_orb_pct REAL,
                away_orb_pct REAL,
                home_ft_rate REAL,
                away_ft_rate REAL,
                pace REAL,
                
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Table 2: Historical Odds (Labels)
        # Primary Key: Composite (date, home, away) to handle unique matchups
        print("Creating Table: nba_historical_odds...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nba_historical_odds (
                id SERIAL PRIMARY KEY,
                game_date_est DATE,
                home_team_norm TEXT,
                away_team_norm TEXT,
                
                odds_source TEXT, -- 'odds_api', 'kaggle'
                odds_type TEXT,   -- 'open', 'close'
                as_of TIMESTAMP,  -- When this line was captured
                
                -- Moneyline
                home_ml_decimal REAL,
                away_ml_decimal REAL,
                
                -- Spread
                home_spread_line REAL,
                home_spread_price REAL,
                away_spread_line REAL,
                away_spread_price REAL,
                
                -- Totals
                total_line REAL,
                over_price REAL,
                under_price REAL,
                
                data_quality_flags TEXT, -- 'clean', 'imputed', 'push'
                
                UNIQUE(game_date_est, home_team_norm, away_team_norm, odds_source)
            );
        """)
        
        conn.commit()
        print("✅ NBA Schema Initialized Successfully.")
        
    except Exception as e:
        print(f"❌ Schema Init Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    init_nba_schema()
