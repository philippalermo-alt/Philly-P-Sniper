import psycopg2
from datetime import datetime
from config import Config
from utils import log, _to_python_scalar

def get_db():
    """Establish database connection."""
    try:
        return psycopg2.connect(Config.DATABASE_URL, sslmode='prefer')
    except Exception as e:
        print(f"❌ [DB ERROR] {e}")
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
            trigger_type TEXT
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

        # KenPom Metrics
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence_log' AND column_name='home_adj_em'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_adj_em REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_adj_em REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_adj_o REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_adj_o REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_adj_d REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_adj_d REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS home_tempo REAL")
            cur.execute("ALTER TABLE intelligence_log ADD COLUMN IF NOT EXISTS away_tempo REAL")

        # Create Settings Table
        cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")

        # Insert default bankroll if not exists
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', '451.16') ON CONFLICT (key) DO NOTHING")

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
            print(f"❌ [DB ERROR] {e}")
            cur.connection.rollback()
        except Exception:
            pass
        return None

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
