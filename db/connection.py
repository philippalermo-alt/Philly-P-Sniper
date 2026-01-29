import psycopg2
from psycopg2 import pool
from datetime import datetime
from config.settings import Config
from utils.logging import log
from utils.math import _to_python_scalar

# Global Connection Pool Container (Lazy Init)
_db_pool = None

def _ensure_pool():
    """Ensure the connection pool is initialized (Thread-Safe logic needed if multi-threaded, but single pipelined for now)."""
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,
                Config.DATABASE_URL,
                sslmode='prefer'
            )
            log("DB", "Connection Pool Initialized (1-20 conns)")
        except Exception as e:
            print(f"❌ DB Pool Error: {e}")
            _db_pool = None
    return _db_pool

class PooledConnection:
    """
    Proxy for psycopg2 connection that returns to pool on close().
    """
    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn
        self._closed = False # Track state

    def close(self):
        """
        Return the connection to the pool.
        """
        if self._conn and not self._closed:
            try:
                self._pool.putconn(self._conn)
                self._conn = None
                self._closed = True
            except Exception as e:
                log("WARN", f"Failed to return conn to pool: {e}")

    def __del__(self):
        """Safety Net: Return to pool on GC."""
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __getattr__(self, name):
        """
        Delegate all other attribute access to the underlying connection.
        """
        return getattr(self._conn, name)

def get_db():
    """
    Get a connection from the pool wrapped in a proxy.
    Lazily initializes pool if needed.
    """
    pool = _ensure_pool()
    if not pool:
        # Fallback if pool failed
        try:
            return psycopg2.connect(Config.DATABASE_URL, sslmode='prefer')
        except Exception as e:
            log("ERROR", f"DB Connect Error: {e}")
            return None

    try:
        conn = pool.getconn()
        if conn:
            return PooledConnection(pool, conn)
    except Exception as e:
        log("ERROR", f"Pool Exhausted/Error: {e}")
        return None

def init_db():
    """Initialize database schema with all required tables and columns."""
    log("DB", "Initializing database schema...")
    conn = get_db()
    if not conn:
        return

    cur = conn.cursor()
    try:
        # Create main intelligence_log table
        cur.execute('''CREATE TABLE IF NOT EXISTS intelligence_log (
            event_id TEXT PRIMARY KEY,
            timestamp TIMESTAMP,
            kickoff TIMESTAMP,
            sport TEXT,
            teams TEXT,
            selection TEXT,
            odds REAL,
            true_prob REAL,
            edge REAL,
            stake REAL,
            outcome TEXT DEFAULT 'PENDING',
            user_bet BOOLEAN DEFAULT FALSE,
            closing_odds REAL,
            ticket_pct INTEGER,
            money_pct INTEGER,
            trigger_type TEXT,
            book TEXT
        )''')
        
        # Phase 2: Calibration Logging (Truth Table)
        cur.execute('''CREATE TABLE IF NOT EXISTS calibration_log (
            id SERIAL PRIMARY KEY,
            event_id TEXT,
            timestamp TIMESTAMP,
            predicted_prob REAL,
            bucket TEXT,
            outcome TEXT DEFAULT 'PENDING'
        )''')

        # Check if sharp_score column exists before trying to ALTER
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='sharp_score'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS sharp_score INTEGER")

        # Add user_odds and user_stake columns
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='user_odds'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS user_odds REAL")

        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='user_stake'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS user_stake REAL")

        # Phase 2 Metrics: xG and DvP
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='home_xg'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_xg REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_xg REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS dvp_rank REAL")

        # KenPom Metrics (Extended)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='home_adj_o'")
        if not cur.fetchone():
            columns = [
                "home_adj_o REAL", "away_adj_o REAL",
                "home_adj_d REAL", "away_adj_d REAL",
                "home_tempo REAL", "away_tempo REAL",
                "home_adj_em REAL", "away_adj_em REAL"
            ]
            for col in columns:
                cur.execute(f"ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS {col}")
        
        # Explicit check for adj_em in case other columns existed but this one didnt
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='home_adj_em'")
        if not cur.fetchone():
             cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_adj_em REAL")
             cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_adj_em REAL")

        # Phase 5: Schedule Fatigue
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='home_rest'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_rest INTEGER")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_rest INTEGER")
            
        # Logic for settlement explanation
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='logic'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS logic TEXT")
            
        # Referees (Phase 5)
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='ref_1'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS ref_1 TEXT")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS ref_2 TEXT")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS ref_3 TEXT")

        # Player Stats Table (Understat)
        cur.execute('''CREATE TABLE IF NOT EXISTS player_stats (
            id SERIAL PRIMARY KEY,
            match_id TEXT,
            player_id TEXT,
            team_id TEXT,
            team_name TEXT,
            player_name TEXT,
            position TEXT,
            minutes INTEGER,
            shots INTEGER,
            goals INTEGER,
            assists INTEGER,
            xg REAL,
            xa REAL,
            xg_chain REAL,
            xg_buildup REAL,
            season TEXT,
            league TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(match_id, player_id)
        )''')

        # Matches Table (Understat Metadata)
        cur.execute('''CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY,
            league TEXT,
            season TEXT,
            date TIMESTAMP,
            home_team TEXT,
            away_team TEXT,
            home_goals INTEGER,
            away_goals INTEGER,
            home_xg REAL,
            away_xg REAL,
            forecast_w REAL,
            forecast_d REAL,
            forecast_l REAL,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Posted Tweets Table (For Recap)
        cur.execute('''CREATE TABLE IF NOT EXISTS posted_tweets (
            id SERIAL PRIMARY KEY,
            event_id TEXT,
            sport TEXT,
            match_name TEXT,
            selection TEXT,
            odds REAL,
            stake REAL,
            tweet_text TEXT,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create Settings Table
        cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")

        # Insert default bankroll if not exists
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', '451.16') ON CONFLICT (key) DO NOTHING")

        # Phase 8: NBA Learning Loop (Predictions)
        cur.execute('''CREATE TABLE IF NOT EXISTS nba_predictions (
            id SERIAL PRIMARY KEY,
            run_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            game_id TEXT,
            game_date_est DATE,
            home_team TEXT,
            away_team TEXT,
            market TEXT, -- 'ML' or 'TOTAL'
            book TEXT,
            
            -- ML Odds
            odds_home REAL,
            odds_away REAL,
            
            -- Totals Odds
            total_line REAL,
            odds_over REAL,
            odds_under REAL,
            
            odds_as_of TIMESTAMP,
            
            -- Versioning
            model_version TEXT,
            model_sha TEXT,
            feature_version TEXT,
            
            -- ML Outputs
            prob_home REAL,
            prob_away REAL,
            
            -- Totals Outputs
            expected_total REAL,
            prob_over REAL,
            prob_under REAL,
            sigma_bucket TEXT,
            z_score REAL,
            
            -- Decision Logic
            edge_pct REAL,
            ev REAL,
            bucket TEXT,
            decision TEXT, -- 'ACCEPT' or 'REJECT'
            reject_reason TEXT,
            
            -- Audit
            features_snapshot JSONB
        )''')
        
        # Phase 8: NBA Outcomes
        cur.execute('''CREATE TABLE IF NOT EXISTS nba_outcomes (
            game_id TEXT PRIMARY KEY,
            game_date_est DATE,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            total_points INTEGER,
            home_win INTEGER, -- 0 or 1
            settled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Phase 8: NBA Training Runs
        cur.execute('''CREATE TABLE IF NOT EXISTS nba_training_runs (
            train_run_id TEXT PRIMARY KEY,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            dataset_start DATE,
            dataset_end DATE,
            n_samples INTEGER,
            
            -- Metrics
            logloss_ml REAL,
            roi_ml REAL,
            roi_coin REAL,
            roi_dog REAL,
            mae_total REAL,
            roi_total_ev5 REAL,
            roi_total_ev7 REAL,
            
            accepted BOOLEAN,
            
            -- Artifacts
            model_path_ml TEXT,
            model_path_total TEXT,
            sigma_path_total TEXT,
            git_sha TEXT
        )''')

        conn.commit()
    except Exception as e:
        print(f"❌ [DB INIT] {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def safe_execute(cur, sql, params=None):
    """
    Execute a parameterized SQL statement while:
    - coercing numpy scalars to native Python types
    - rolling back the current transaction on error so subsequent statements can run
    """
    try:
        if params is None:
            return cur.execute(sql)
        normalized = tuple(_to_python_scalar(p) for p in params)
        return cur.execute(sql, normalized)
    except Exception as e:
        try:
            # SAFETY FIX: Log Critical Errors loudly AND RAISE
            print(f"❌ [DB CRITICAL] Query Failed: {sql[:100]}... Error: {e}")
            cur.connection.rollback()
        except Exception:
            pass
        # Raise the original error to stop execution flow
        raise e

def log_calibration(event_id, prob):
    """Log prediction for calibration tracking (Phase 2)."""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        bucket = f"{int(prob * 20) * 5}-{int(prob * 20) * 5 + 5}%" # e.g. 50-55%
        
        cur.execute("""
            INSERT INTO calibration_log (event_id, timestamp, predicted_prob, bucket)
            VALUES (%s, NOW(), %s, %s)
        """, (event_id, prob, bucket))
        conn.commit()
    except Exception as e:
        print(f"❌ Calib Log Error: {e}")
    finally:
        conn.close()

def get_calibration(sport):
    """Calculate calibration factor based on historical performance."""
    conn = get_db()
    if not conn:
        return 1.0

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT true_prob, outcome FROM intelligence_log WHERE sport = %s AND outcome IN ('WON', 'LOST')",
            (sport,)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if len(rows) < 10:
            return 1.0

        predicted = sum(r[0] for r in rows) / len(rows)
        actual = sum(1 for r in rows if r[1] == 'WON') / len(rows)

        if predicted == 0:
            return 1.0

        return max(0.85, min(actual / predicted, 1.15))
    except:
        return 1.0

def get_last_update_time():
    """Fetch the timestamp of the last scanner run."""
    conn = get_db()
    if not conn:
        return "Unknown"
    
    try:
        cur = conn.cursor()
        
        # 1. Try fetching explicit 'model_last_run' from settings (Most Accurate)
        cur.execute("SELECT value FROM app_settings WHERE key='model_last_run'")
        row = cur.fetchone()
        
        ts = None
        if row and row[0]:
            ts = row[0]
        else:
            # 2. Fallback to max timestamp in log
            cur.execute("SELECT MAX(timestamp) FROM intelligence_log")
            row = cur.fetchone()
            if row and row[0]:
                ts = row[0]
                
        cur.close()
        conn.close()
        
        if ts:
             # Format nicely
            if isinstance(ts, str):
                try:
                    # Fix Postgres format "2026-01-25 18:03:50+00" -> "2026-01-25T18:03:50+00:00"
                    if ' ' in ts and 'T' not in ts:
                        ts = ts.replace(' ', 'T')
                    if ts.endswith('+00'):
                        ts = ts + ':00'
                    ts = datetime.fromisoformat(ts)
                except Exception as e:
                    # Fallback manually parsing if really needed, or just return nicely
                    try:
                        # Simple split fallback
                        return ts.split('.')[0].replace('T', ' ') + " UTC"
                    except:
                        pass

            # If it's a datetime object
            if hasattr(ts, 'strftime'):
                import pytz
                # Assume UTC if naive, as DB stores UTC
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=pytz.utc)
                
                eastern = pytz.timezone('US/Eastern')
                ts_est = ts.astimezone(eastern)
                # User requested format: 1:22:00 PM
                return ts_est.strftime('%I:%M:%S %p').lstrip('0')
            return str(ts)

        return "Never"
    except Exception as e:
        log("ERROR", f"Timestamp fetch failed: {e}")
        return "Error"

def get_dynamic_bankroll():
    """
    Calculate real-time bankroll (Starting + PnL).
    Fetches starting bankroll from app_settings and adds sum of realized PnL.
    """
    conn = get_db()
    if not conn:
        return float(Config.BANKROLL) # Fallback

    try:
        cur = conn.cursor()
        
        # 1. Get Starting Bankroll
        cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
        row = cur.fetchone()
        start = float(row[0]) if row else float(Config.BANKROLL)
        
        # 2. Get Realized PnL
        # Won: Stake * (Odds - 1)
        # Lost: -Stake
        cur.execute("""
            SELECT sum(case 
                when outcome='WON' then (user_stake * (user_odds - 1)) 
                when outcome='LOST' then -user_stake 
                else 0 end) 
            FROM intelligence_log 
            WHERE outcome IN ('WON', 'LOST', 'PUSH') 
            AND user_bet = TRUE
        """)
        
        # NOTE: We only count 'user_bet = TRUE' for the bankroll that WE control?
        # User request: "use the tracking feature to log every actual bet I make so that the bankroll stays up to date"
        # So yes, we should only sum up user_bet=True?
        # Wait, previous PnL calculation used ALL bets?
        # The user wants "staking recommendations... based on $1,000".
        # If I use `user_bet = TRUE`, then the PnL will be 0 initially (if no user bets tracked yet).
        # But if the user wants to "start today", then PnL usually means PnL going FORWARD.
        # However, to preserve history, I'm setting starting_bankroll to 1041.51 and calculating TOTAL PnL.
        row = cur.fetchone()
        
        # NOTE: Current logic sums correct/incorrect logic for bankroll? No, using user_bet.
        # This function returns TOTAL bankroll.
        
        realized_pnl = float(row[0]) if row and row[0] else 0.0
        
        cur.close()
        conn.close()
        
        return start + realized_pnl
    except Exception as e:
        log("ERROR", f"Bankroll Calc Error: {e}")
        return float(Config.BANKROLL)

def get_starting_bankroll():
    """Get the manually set starting bankroll."""
    conn = get_db()
    if not conn: return 1000.0
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
        row = cur.fetchone()
        return float(row[0]) if row else 1000.0
    except:
        return 1000.0
    finally:
        conn.close()

def update_bankroll(val):
    """Update starting bankroll setting."""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        # Upsert
        cur.execute("""
            INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (str(val),))
        conn.commit()
    except Exception as e:
        print(f"Update Bankroll Error: {e}")
    finally:
        conn.close()

def surgical_cleanup():
    """Remove ghost bets (Pending > 24h ago)."""
    conn = get_db()
    if not conn: return
    try:
        cur = conn.cursor()
        # 1. Clean Stale Past Bets (Older than 24h)
        cur.execute("DELETE FROM intelligence_log WHERE outcome='PENDING' AND kickoff < NOW() - INTERVAL '24 HOURS'")
        count_past = cur.rowcount
        
        # 2. Clean Far Future Bets (Beyond 36h limit)
        # This removes the "Ghost Bets" from before the rule change
        cur.execute("DELETE FROM intelligence_log WHERE outcome='PENDING' AND kickoff > NOW() + INTERVAL '36 HOURS'")
        count_future = cur.rowcount
        
        conn.commit()
        print(f"🧹 Cleanup: Removed {count_past} stale past bets and {count_future} far-future bets.")
    except Exception as e:
        print(f"Cleanup Error: {e}")
    finally:
        conn.close()
