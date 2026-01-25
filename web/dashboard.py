
import streamlit as st
import pandas as pd
import psycopg2
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load env immediately
load_dotenv()

import difflib
import textwrap
from processing.backtesting import analyze_by_edge_bucket, analyze_clv
from processing.parlay import generate_parlays
import re
from db.connection import get_db, get_last_update_time, get_starting_bankroll, update_bankroll, surgical_cleanup

def check_auth(module_name="Admin"):
    """Simple authorization check."""
    # Could check st.session_state['authenticated'] here
    return True

def get_sharp_badge(row):
    """Generate HTML badge with Tiered Status + Money/Ticket splits."""
    try:
        val = row.get('sharp_score')
        
        # Robust conversion
        try:
            score = float(val)
        except (ValueError, TypeError):
            # If conversion fails (None, string, etc), treat as No Signal
            return "<span style='color: #94A3B8; font-size: 10px; font-weight: 600; background: #1E293B; border: 1px solid #334155; padding: 1px 4px; border-radius: 4px;'>📡 NO SIGNAL</span>"

        if pd.isna(score):
            return "<span style='color: #94A3B8; font-size: 10px; font-weight: 600; background: #1E293B; border: 1px solid #334155; padding: 1px 4px; border-radius: 4px;'>📡 NO SIGNAL</span>"
        
        # Safely get Money/Ticket stats
        try:
            money = int(float(row.get('money_pct') or 0))
            ticket = int(float(row.get('ticket_pct') or 0))
        except:
            money, ticket = 0, 0
        
        if score >= 70:
             badge = "<span style='background: linear-gradient(90deg, #F59E0B, #D97706); color: black; padding: 2px 6px; border-radius: 4px; font-weight: 800; font-size: 10px; box-shadow: 0 0 5px rgba(245,158,11,0.5);'>🔥 SHARP</span>"
        elif score >= 45:
             badge = "<span style='background: #3B82F6; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10px;'>🔵 LEAN</span>"
        elif score >= 25:
             badge = "<span style='background: #64748B; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 600; font-size: 10px;'>⚪ NEUTRAL</span>"
        else:
             # If score is low (<25), check if we actually have data
             if money == 0 and ticket == 0:
                  return "<span style='color: #94A3B8; font-size: 10px; font-weight: 600; background: #1E293B; border: 1px solid #334155; padding: 1px 4px; border-radius: 4px;'>📡 NO SIGNAL</span>"
             
             badge = "<span style='background: #EF4444; color: white; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 10px;'>⛔ PUBLIC</span>"
             
        stats = f"<span style='color: #94A3B8; margin-left: 6px; font-size: 10px; font-family: monospace;'>💰{money}% 🎟️{ticket}%</span>"
        
        return f"{badge} {stats}"

    except Exception as e:
        # Last resort fallback
        return "<span style='color: #64748B; font-size: 10px;'>...</span>"

def clean_html(html_str):
    """Flatten HTML string to single line to avoid Markdown interpreting indentation as code blocks."""
    return re.sub(r'\s+', ' ', html_str).strip()

# 🎨 Modern Page Configuration
st.set_page_config(
    page_title="PhillyEdge.AI",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# 🎨 Custom CSS for Modern Look - DARK MODE V5
st.markdown(clean_html("""
<style>
    /* Main background - Deep Navy */
    .stApp {
        background-color: #0B1120;
    }
    .main {
        background-color: #0B1120;
    }

    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #0B1120 !important;
        border-right: 1px solid #334155;
    }
    [data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }

    /* Headers - Gold & White */
    h1 {
        color: #F59E0B !important; /* Gold */
        font-weight: 800;
        letter-spacing: 1px;
        text-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-transform: uppercase;
    }

    h2, h3 {
        color: #F8FAFC !important; /* Slate 50 */
        font-weight: 700;
        border-bottom: 2px solid #F59E0B; /* Gold underline for sections */
        padding-bottom: 8px;
        display: inline-block;
    }

    h4, h5, h6 {
        color: #E2E8F0 !important; /* Slate 200 */
    }

    /* Text */
    p, label, span, div, li {
        color: #CBD5E1; /* Slate 300 */
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #F59E0B !important; /* Gold */
        text-shadow: 0 0 10px rgba(245, 158, 11, 0.3); /* Glow */
    }

    [data-testid="stMetricLabel"] {
        color: #94A3B8 !important; /* Slate 400 */
        font-size: 14px !important;
    }

    /* Cards (Containers) */
    [data-testid="stHorizontalBlock"], .stContainer {
        background-color: #1E293B; /* Slate 800 */
        border: 1px solid #334155; /* Slate 700 */
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    
    /* Buttons - Gold Gradient */
    .stButton > button {
        background: linear-gradient(135deg, #B45309 0%, #F59E0B 100%); /* Gold/Dark Gold */
        color: #ffffff;
        border: 1px solid #F59E0B;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #F59E0B 0%, #FCD34D 100%);
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.5);
        color: #000;
        border-color: #FFF;
    }

    /* Popover Buttons (Track) - Force Gold */
    /* Popover Buttons (Track) - Force Gold (Multiple Selectors) */
    [data-testid="stPopover"] button,
    [data-testid="stPopover"] > button,
    [data-testid="stPopover"] > div > button {
        background: linear-gradient(135deg, #B45309 0%, #F59E0B 100%) !important;
        color: #ffffff !important;
        border: 1px solid #F59E0B !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
    }
    [data-testid="stPopover"] button:hover,
    [data-testid="stPopover"] > button:hover,
    [data-testid="stPopover"] > div > button:hover {
        background: linear-gradient(135deg, #F59E0B 0%, #FCD34D 100%) !important;
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.5) !important;
        color: #000 !important;
        border-color: #FFF !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1E293B;
        border: 1px solid #334155;
    }
    
    /* ... existing styles ... */
    
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
    }

    .stTabs [aria-selected="true"] {
        background-color: #F59E0B !important;
        color: #000000 !important;
        font-weight: bold;
    }
    
    /* ... */
</style>
    
    <script>
    // Force "Track" buttons to Gold using MutationObserver
    const observer = new MutationObserver(() => {
        const buttons = window.parent.document.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.innerText.includes("✅ Track") || btn.innerText.includes("✅ TRACK")) {
                btn.style.background = "linear-gradient(135deg, #B45309 0%, #F59E0B 100%)";
                btn.style.color = "white";
                btn.style.border = "1px solid #F59E0B";
                btn.style.fontWeight = "700";
                btn.style.textTransform = "uppercase";
                btn.style.boxShadow = "0 4px 6px rgba(0,0,0,0.3)";
            }
        });
    });
    observer.observe(window.parent.document.body, { childList: true, subtree: true });
    </script>
"""), unsafe_allow_html=True)

# ... (skip to confirm_bet)

def confirm_bet(event_id, odds, stake):
    print(f"🔥 [DASHBOARD] Callback Triggered: Confirm {event_id} @ {odds} / ${stake}", flush=True)
    conn = get_db()
    
    if not conn:
        print("❌ [DASHBOARD] DB Connection Failed in Callback", flush=True)
        st.session_state['toast_msg'] = ("❌ DB Connection Failed", "error")
        return

    try:
        cur = conn.cursor()
        print(f"   ✅ [DASHBOARD] Executing UPDATE for {event_id}", flush=True)
        
        # Set user_bet to TRUE and update odds/stake
        cur.execute("""
            UPDATE intelligence_log 
            SET user_bet = TRUE, user_odds = %s, user_stake = %s 
            WHERE event_id = %s
        """, (float(odds), float(stake), str(event_id)))
        
        rows = cur.rowcount
        conn.commit()
        cur.close()
        
        print(f"   ✅ [DASHBOARD] Rows affected: {rows}", flush=True)
        
        if rows > 0:
            st.session_state['toast_msg'] = (f"✅ Tracked bet {event_id}", "success")
        else:
            st.session_state['toast_msg'] = (f"⚠️ Event ID {event_id} not found.", "warning")
            
    except Exception as e:
        print(f"❌ [DASHBOARD] Error: {e}", flush=True)
        st.session_state['toast_msg'] = (f"❌ Error tracking bet: {e}", "error")

# ... (skip to cancel_bet_db)

def cancel_bet_db(event_id):
    print(f"🔥 [DASHBOARD] Callback Triggered: Cancel {event_id}", flush=True)
    conn = get_db()
    
    if not conn:
        print("❌ [DASHBOARD] DB Connection Failed in Callback", flush=True)
        st.session_state['toast_msg'] = ("❌ DB Connection Failed", "error")
        return

    try:
        cur = conn.cursor()
        print(f"   ❌ [DASHBOARD] Executing UPDATE for {event_id}", flush=True)
        
        # Set user_bet to FALSE
        cur.execute("UPDATE intelligence_log SET user_bet = FALSE WHERE event_id = %s", (str(event_id),))
        rows = cur.rowcount
        conn.commit()
        cur.close()
        
        print(f"   ✅ [DASHBOARD] Rows affected: {rows}", flush=True)
        
        if rows > 0:
            st.session_state['toast_msg'] = (f"✅ Cancelled bet {event_id}", "success")
        else:
            st.session_state['toast_msg'] = (f"⚠️ Event ID {event_id} not found or already cancelled.", "warning")
            
    except Exception as e:
        print(f"❌ [DASHBOARD] Error: {e}", flush=True)
        st.session_state['toast_msg'] = (f"❌ Error cancelling bet: {e}", "error")


def confirm_parlay(event_id, odds, stake, selection_text, legs_desc):
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check if already exists
        cur.execute("SELECT event_id FROM intelligence_log WHERE event_id = %s", (event_id,))
        if cur.fetchone():
            return # Already tracked
            
        cur.execute("""
            INSERT INTO intelligence_log 
            (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, user_bet, user_odds, user_stake, outcome)
            VALUES (%s, NOW(), NOW(), 'PARLAY', 'Edge Triple', %s, %s, 0, 0, %s, TRUE, %s, %s, 'PENDING')
        """, (event_id, selection_text, odds, stake, odds, stake))
        
        conn.commit()
        cur.close()
        st.rerun()
    except Exception as e:
        st.error(f"Error tracking parlay: {e}")

# --- Data Fetching ---
@st.cache_data(ttl=60)
def fetch_live_games(sport_keys):
    """
    Fetch live scores from ESPN's public hidden API (Free).
    """
    games = []
    logs = []
    
    unique_sports = set(sport_keys)
    
    # Map internal keys to ESPN API paths
    ESPN_MAP = {
        'basketball_nba': 'basketball/nba',
        'NBA': 'basketball/nba',
        'basketball_ncaab': 'basketball/mens-college-basketball',
        'NCAAB': 'basketball/mens-college-basketball',
        'icehockey_nhl': 'hockey/nhl',
        'NHL': 'hockey/nhl',
        'americanfootball_nfl': 'football/nfl',
        'NFL': 'football/nfl',
        'baseball_mlb': 'baseball/mlb',
        'MLB': 'baseball/mlb',
        'soccer_epl': 'soccer/eng.1',
        'SOCCER': 'soccer/eng.1',
    }

    processed_paths = set()
    import pytz
    tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz)
    date_str = now_et.strftime('%Y%m%d')

    for sport_key in unique_sports:
        espn_path = ESPN_MAP.get(sport_key)
        if not espn_path or espn_path in processed_paths:
            continue
            
        processed_paths.add(espn_path)

        try:
            base_url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={date_str}"
            if 'college-basketball' in espn_path:
                base_url += "&groups=50&limit=900"
            url = base_url
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)
            
            if r.status_code == 200:
                res = r.json()
                events = res.get('events', [])
                for event in events:
                    comp = event['competitions'][0]
                    status_detail = event.get('status', {}).get('type', {}).get('shortDetail', 'Scheduled')
                    
                    competitors = comp.get('competitors', [])
                    home_comp = next((c for c in competitors if c['homeAway'] == 'home'), {})
                    away_comp = next((c for c in competitors if c['homeAway'] == 'away'), {})
                    
                    h_name = home_comp.get('team', {}).get('displayName', 'Home')
                    a_name = away_comp.get('team', {}).get('displayName', 'Away')
                    h_score = home_comp.get('score', '0')
                    a_score = away_comp.get('score', '0')
                    
                    games.append({
                        'home': h_name,
                        'away': a_name,
                        'score': f"{status_detail}: {a_name} {a_score} - {h_name} {h_score}"
                    })
        except Exception as e:
            logs.append(f"❌ {sport_key}: {e}")

    return games, logs

# --- Header ---
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    try:
        if os.path.exists("assets/logo.png"):
             col2.markdown("<style>[data-testid='stImage'] {display: flex; justify_content: center;}</style>", unsafe_allow_html=True)
             st.image("assets/logo.png", use_container_width=False)
        else:
             st.markdown("<h1 style='text-align: center; color: #F59E0B;'>🎯 PHILLY EDGE: AI</h1>", unsafe_allow_html=True)
    except:
        st.markdown("<h1 style='text-align: center; color: #F59E0B;'>🎯 PHILLY EDGE: AI</h1>", unsafe_allow_html=True)

st.markdown("---")

# --- Main Database Connection ---
conn = get_db()

# --- Sidebar ---
with st.sidebar:
    # --- Last Updated Timestamp (Moved to Top) ---
    last_run = get_last_update_time()
    st.caption(f"Last Updated: {last_run}")
    st.divider()

    with st.expander("📰 News Intel (Live)", expanded=True):
        try:
            from news_client import NewsClient
            @st.cache_data(ttl=3600)
            def load_cached_news():
                nc = NewsClient()
                return nc.get_all_news()

            if 'news_data' not in st.session_state:
                st.session_state['news_data'] = load_cached_news()
            
            if st.button("🔄 Refresh News", key="btn_ref_news"):
                st.cache_data.clear()
                st.session_state['news_data'] = load_cached_news()
                st.rerun()

            news_items = st.session_state['news_data']
            if news_items:
                for item in news_items[:8]:
                    st.markdown(f"**{item['badge']}**")
                    st.caption(f"{item['headline']}")
                    st.markdown(f"<a href='{item['link']}' target='_blank' style='color: #60A5FA;'>Read ➤</a>", unsafe_allow_html=True)
                    st.divider()
        except Exception as e:
            st.error(f"News: {e}")



    st.markdown("### ⚙️ Settings")
    st.caption("Admin controls moved to 'Admin Tools' tab.")
    
    st.divider()
    st.markdown("### 🎛️ Filters")
    sharp_filter = st.slider("Min Sharp Score", 0, 100, 0)
    
    c1, c2 = st.columns(2)
    with c1: min_edge_filter = st.number_input("Min Edge %", 0.0, 100.0, 0.0, 0.5)
    with c2: max_edge_filter = st.number_input("Max Edge %", 0.0, 100.0, 100.0, 0.5)

    # --- RESTORED SPORT FILTER ---
    all_sports = sorted(list(set(pd.read_sql("SELECT DISTINCT sport FROM intelligence_log", conn)['sport'].tolist()))) if conn else []
    # Clean up sport names for display
    display_sports = [s.replace('basketball_', '').replace('americanfootball_', '').replace('icehockey_', '').replace('soccer_', '').upper() for s in all_sports]
    
    selected_sports = st.multiselect("Filter Sport", display_sports, default=[])

    mobile_view = st.checkbox("📱 Mobile View", value=False)
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()


# --- Main Dashboard Logic ---
# conn = get_db() # Using existing conn from top
if conn:
    try:
        # Check Toast Queue
        if 'toast_msg' in st.session_state:
            msg, type_ = st.session_state['toast_msg']
            if type_ == 'success': st.success(msg)
            elif type_ == 'error': st.error(msg)
            elif type_ == 'warning': st.warning(msg)
            del st.session_state['toast_msg']
            
        # Fetch Data
        df_p = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome = 'PENDING' AND timestamp >= NOW() - INTERVAL '24 HOURS' ORDER BY kickoff ASC LIMIT 500", conn)
        df_s = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome IN ('WON', 'LOST', 'PUSH') ORDER BY kickoff DESC", conn)
        conn.commit()

        def clean_df(df):
            if df.empty: return df
            df['kickoff'] = pd.to_datetime(df['kickoff']).dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert('US/Eastern')
            df['Date'] = df['kickoff'].dt.strftime('%Y-%m-%d')
            df['Kickoff'] = df['kickoff'].dt.strftime('%m-%d %H:%M')
            df['Sport'] = df['sport'].apply(lambda x: x.split('_')[-1].upper() if '_' in x else x)
            df['Event'] = df['teams']
            df['Selection'] = df['selection']

            def get_val(row, col_base):
                user_col = f"user_{col_base}"
                if user_col in row and pd.notnull(row[user_col]): return float(row[user_col])
                return float(row[col_base]) if pd.notnull(row[col_base]) else 0.0

            df['Stake_Val'] = df.apply(lambda row: get_val(row, 'stake'), axis=1)
            df['Stake_Val'] = df['Stake_Val'].apply(lambda x: max(1.00, x))
            df['Stake'] = df['Stake_Val'].apply(lambda x: f"${x:.2f}")
            df['Dec_Odds'] = df.apply(lambda row: get_val(row, 'odds'), axis=1)
            df['Edge_Val'] = pd.to_numeric(df['edge'], errors='coerce').fillna(0)
            df['Edge'] = df['Edge_Val'].apply(lambda x: f"{x*100:.1f}%")
            return df

        df_pending = clean_df(df_p)
        df_settled = clean_df(df_s)

        # Apply Sport Filter
        if selected_sports:
            df_pending = df_pending[df_pending['Sport'].isin(selected_sports)]
            df_settled = df_settled[df_settled['Sport'].isin(selected_sports)]

        # --- TIMESTAMP & HEADER ---
        st.markdown("---")
        last_run = get_last_update_time()
        st.markdown(f"<div style='text-align: center; color: #FFFFFF; font-size: 14px; font-weight: 700; margin-bottom: 20px;'>🕒 Last Updated: {last_run}</div>", unsafe_allow_html=True)

        # Tab Structure
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Live Edge Feed", "💼 Active Portfolio", "⚽ Player Prop Edges", "🛠️ Admin & Analytics", "👁️ Truth (Calibration)"])
        
        with tab1:
            if not df_pending.empty:
                # Common Vars
                now_est = pd.Timestamp.now(tz='US/Eastern')
                
                # --- SECTION 1: TOP 15 OPPORTUNITIES ---
                st.markdown("### ⚡ Top 15 Opportunities")
                st.caption("Best value plays from every available sport, sorted by kickoff.")
                
                # Base Filter: Future Games + Not Bet + Edge 3-15% + NOT PROPS
                top_pool = df_pending[
                    (df_pending['user_bet'] == False) & 
                    (df_pending['kickoff'] > now_est) &
                    (df_pending['Edge_Val'] >= 0.03) & 
                    (df_pending['Edge_Val'] <= 0.15) &
                    (~df_pending['event_id'].astype(str).str.startswith('PROP_'))
                ].copy()
                
                top_picks = []
                if not top_pool.empty:
                    # Strategy: Get best (highest edge) from each sport first
                    sports = top_pool['Sport'].unique()
                    used_indices = set()
                    
                    # 1. One "Best" per Sport
                    for sport in sports:
                        sport_df = top_pool[top_pool['Sport'] == sport].sort_values('Edge_Val', ascending=False)
                        if not sport_df.empty:
                            best_row = sport_df.iloc[0]
                            top_picks.append(best_row)
                            used_indices.add(best_row.name)
                    
                    # 2. Fill remainder up to 15 with best remaining by Edge (highest first)
                    remaining_slots = 15 - len(top_picks)
                    if remaining_slots > 0:
                        rest_df = top_pool[~top_pool.index.isin(used_indices)]
                        # Get highest edges first
                        rest_df = rest_df.sort_values('Edge_Val', ascending=False)
                        top_picks.extend([r for _, r in rest_df.head(remaining_slots).iterrows()])
                    
                    # 3. Final Sort of the Top 15 List: Kickoff Time (Ascending)
                    final_top_df = pd.DataFrame(top_picks).sort_values('kickoff', ascending=True)
                    
                    # Render Cards
                    t_cols = st.columns(3)
                    for idx, (_, row) in enumerate(final_top_df.iterrows()):
                        badge = get_sharp_badge(row)
                        with t_cols[idx % 3]:
                            st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #F59E0B; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                    {badge}
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                                <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                    <div>
                                        <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                        <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']}</div>
                                    </div>
                                    <div style='text-align: right;'>
                                        <div style='color: #94A3B8; font-size: 10px;'>STAKE</div>
                                        <div style='color: #F59E0B; font-weight: 700; font-size: 14px;'>{row['Stake']}</div>
                                    </div>
                                </div>
                            </div>
                            """), unsafe_allow_html=True)
                            with st.popover("✅ Track", use_container_width=True):
                                u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), key=f"t_uo_{row['event_id']}")
                                u_stake = st.number_input("Stake", value=float(row['Stake_Val']), key=f"t_us_{row['event_id']}")
                                
                                # Dynamic Edge Calc
                                true_prob = float(row.get('true_prob', 0))
                                if true_prob > 1: true_prob = true_prob / 100.0 # Normalize percentage
                                
                                if true_prob > 0:
                                    # Standardized Formula: Prob Diff (Model - Implied)
                                    implied = 1.0 / u_odds if u_odds > 0 else 0
                                    calc_edge = true_prob - implied
                                        
                                    edge_color = "#10B981" if calc_edge > 0 else "#EF4444"
                                    st.markdown(f"<div style='margin-bottom: 8px; font-size: 13px;'>Win Prob: <b style='color: #E2E8F0'>{true_prob*100:.1f}%</b> | Edge: <b style='color: {edge_color}'>{calc_edge*100:.1f}%</b></div>", unsafe_allow_html=True)
                                
                                if st.button("Confirm", key=f"t_btn_{row['event_id']}", use_container_width=True):
                                    confirm_bet(row['event_id'], u_odds, u_stake)
                else:
                    st.info("No plays found fitting the Top 15 criteria (3-15% Edge).")

                st.divider()

                # --- SECTION 2: SHARP INTEL (Score >= 70) ---
                st.markdown("### 🧠 Sharp Intel")
                st.info("ℹ️ **Explainer**: These plays feature high Sharp Scores (>= 70), indicating significant 'Smart Money' action (High Money % vs Low Ticket %). They may not fit our statistical model's edge criteria, but the market is moving heavily on them.")
                
                sharp_pool = df_pending[
                    (df_pending['user_bet'] == False) & 
                    (df_pending['kickoff'] > now_est) &
                    (pd.to_numeric(df_pending['sharp_score'], errors='coerce') >= 70)
                ].copy()
                
                if not sharp_pool.empty:
                    sharp_pool = sharp_pool.sort_values('kickoff', ascending=True)
                    # s_cols = st.columns(3) <--- REMOVED COLUMNS
                    for idx, (_, row) in enumerate(sharp_pool.iterrows()):
                         badge = get_sharp_badge(row)
                         # with s_cols[idx % 3]: <--- REMOVED CONTEXT MANAGER
                         st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #60A5FA; margin-bottom: 12px; opacity: 0.9;'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                    {badge}
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                            </div>
                            """), unsafe_allow_html=True)
                            # Track button for Sharps too? Optional, keeping it simple for now or adding if requested.
                            # Adding simplified track for consistency
                         with st.popover("Track Sharp", use_container_width=True):
                                confirm_bet(row['event_id'], float(row['Dec_Odds']), float(row['Stake_Val']))
                else:
                     st.caption("No high-conviction sharp signals (70+) detected right now.")
                
                st.divider()

                # --- SECTION 3: ALL OTHER SCANNER RECOMMENDATIONS (Non-Props) ---
                st.markdown("### 📋 Edge Plays")
                st.caption("Comprehensive list of all other value opportunities identified by the scanner (Edges > 0%).")
                
                # Gather IDs already displayed to avoid duplicates
                displayed_ids = set()
                if 'final_top_df' in locals() and not final_top_df.empty:
                    displayed_ids.update(final_top_df['event_id'].tolist())
                if 'sharp_pool' in locals() and not sharp_pool.empty:
                    displayed_ids.update(sharp_pool['event_id'].tolist())

                general_pool = df_pending[
                    (df_pending['user_bet'] == False) &
                    (df_pending['kickoff'] > now_est) &
                    (df_pending['Edge_Val'] >= (min_edge_filter / 100.0)) &
                    (df_pending['Edge_Val'] <= (max_edge_filter / 100.0)) &
                    (~df_pending['event_id'].astype(str).str.startswith('PROP_')) &
                    (~df_pending['event_id'].isin(displayed_ids))
                ].copy()

                if not general_pool.empty:
                    general_pool = general_pool.sort_values('kickoff', ascending=True)
                    g_cols = st.columns(2) # 2 per row
                    for idx, (_, row) in enumerate(general_pool.iterrows()):
                        badge = get_sharp_badge(row)
                        with g_cols[idx % 2]:
                            st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #10B981; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                    {badge}
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                                <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                    <div>
                                        <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                        <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']}</div>
                                    </div>
                                    <div style='text-align: right;'>
                                        <div style='color: #94A3B8; font-size: 10px;'>STAKE</div>
                                        <div style='color: #F59E0B; font-weight: 700; font-size: 14px;'>{row['Stake']}</div>
                                    </div>
                                </div>
                            </div>
                            """), unsafe_allow_html=True)
                            with st.popover("✅ Track", use_container_width=True):
                                u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), key=f"g_uo_{row['event_id']}")
                                u_stake = st.number_input("Stake", value=float(row['Stake_Val']), key=f"g_us_{row['event_id']}")
                                
                                # Dynamic Edge Calc
                                true_prob = float(row.get('true_prob', 0))
                                if true_prob > 1: true_prob = true_prob / 100.0 # Normalize percentage
                                
                                if true_prob > 0:
                                    # Standardized Formula: Prob Diff
                                    implied = 1.0 / u_odds if u_odds > 0 else 0
                                    calc_edge = true_prob - implied
                                        
                                    edge_color = "#10B981" if calc_edge > 0 else "#EF4444"
                                    st.markdown(f"<div style='margin-bottom: 8px; font-size: 13px;'>Win Prob: <b style='color: #E2E8F0'>{true_prob*100:.1f}%</b> | Edge: <b style='color: {edge_color}'>{calc_edge*100:.1f}%</b></div>", unsafe_allow_html=True)

                                if st.button("Confirm", key=f"g_btn_{row['event_id']}", use_container_width=True):
                                    confirm_bet(row['event_id'], u_odds, u_stake)
                else:
                    st.caption("No other value plays detected.")
            else:
                st.info("📭 No pending games found.")

        # --- TAB 2: PORTFOLIO ---
        with tab2:
            my_bets = df_pending[df_pending['user_bet'] == True].copy()
            if my_bets.empty:
                st.info("📭 Portfolio empty.")
            else:
                for idx, row in my_bets.iterrows():
                    with st.container():
                        st.markdown(clean_html(f"""
                        <div style='background: #1E293B; padding: 15px; border-radius: 10px; border-left: 4px solid #F59E0B; margin-bottom: 10px;'>
                            <div style='display: flex; justify-content: space-between;'>
                                <div>
                                    <p style='color: #94A3B8; font-size: 12px; margin: 0;'>{row['Sport']} • {row['Kickoff']}</p>
                                    <h4 style='color: #FFFFFF; font-size: 16px; font-weight: 700; margin: 5px 0;'>{row['Event']}</h4>
                                    <p style='color: #60A5FA; font-size: 14px;'>👉 {row['Selection']} <span style='color: #94A3B8;'>({row['Dec_Odds']})</span></p>
                                </div>
                                <div style='text-align: right;'>
                                    <p style='color: #FFFFFF; font-size: 18px; font-weight: 700;'>{row['Stake']}</p>
                                </div>
                            </div>
                        </div>
                        """), unsafe_allow_html=True)
                        st.button("❌ Cancel", key=f"cancel_{row['event_id']}", on_click=cancel_bet_db, args=(row['event_id'],))


        # --- TAB 3: PLAYER PROP EDGES ---
        with tab3:
            st.markdown("### ⚽ Player Prop Edges")
            
            with st.expander("🔎 Manual Edge Scanner (xG Playmakers)", expanded=False):
                try:
                    from player_props_model import PlayerPropsPredictor
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        pl = st.selectbox("League", ["EPL", "La_liga", "Bundesliga", "Serie_A", "Ligue_1"], key="s_lg")
                        mm = st.slider("Min Minutes", 100, 1000, 400, key="s_mm")
                        if st.button("🔎 Scan", key="s_btn", use_container_width=True):
                            pred = PlayerPropsPredictor(league=pl, season="2025")
                            st.session_state['scan_df'] = pred.scan_for_props_edges(min_minutes=mm)
                    
                    with c2:
                        if 'scan_df' in st.session_state and not st.session_state['scan_df'].empty:
                            sdf = st.session_state['scan_df']
                            t1, t2 = st.tabs(["🎯 Shots", "🧠 Playmakers"])
                            with t1:
                                st.dataframe(sdf.sort_values('proj_shots_p90', ascending=False).head(20)[['player_name','proj_shots_p90','prob_goal']], use_container_width=True, hide_index=True)
                            with t2:
                                st.dataframe(sdf.sort_values('proj_xg_chain_p90', ascending=False).head(20)[['player_name','proj_xg_chain_p90','proj_xa_p90']], use_container_width=True, hide_index=True)
                        else:
                            st.info("Run Scan to see results.")
                except Exception as e:
                    st.error(f"Scanner Err: {e}")

            st.divider()
            # Prop Cards
            # Filter out started games
            prop_df = df_pending[
                (df_pending['event_id'].astype(str).str.startswith('PROP_')) &
                (df_pending['kickoff'] > now_est)
            ].copy()
            if not prop_df.empty:
                # Deduplicate: Keep only the latest scan for the same player/prop/matchup
                # Sort by timestamp desc first to keep the newest
                if 'timestamp' in prop_df.columns:
                    prop_df = prop_df.sort_values('timestamp', ascending=False)
                
                # Drop duplicates based on Selection (Player+Type) and Teams (Matchup)
                prop_df = prop_df.drop_duplicates(subset=['selection', 'teams'], keep='first')
                
                # Re-sort by kickoff for display
                prop_df = prop_df.sort_values('kickoff', ascending=True)

                pcols = st.columns(3)
                for i, (_, row) in enumerate(prop_df.iterrows()):
                    badge = get_sharp_badge(row) # Use badge logic even if sparse for props
                    with pcols[i % 3]:
                        st.markdown(clean_html(f"""
                        <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #3B82F6; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                            <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                {badge}
                            </div>
                            <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                            <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                            </div>
                            <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                <div>
                                    <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                    <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']}</div>
                                </div>
                                <div style='text-align: right;'>
                                    <div style='color: #94A3B8; font-size: 10px;'>STAKE</div>
                                    <div style='color: #F59E0B; font-weight: 700; font-size: 14px;'>{row['Stake']}</div>
                                </div>
                            </div>
                        </div>
                        """), unsafe_allow_html=True)
                        with st.popover("✅ Track", use_container_width=True):
                                u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), key=f"p_uo_{row['event_id']}")
                                u_stake = st.number_input("Stake", value=float(row['Stake_Val']), key=f"p_us_{row['event_id']}")

                                # Dynamic Edge Calc
                                true_prob = float(row.get('true_prob', 0))
                                if true_prob > 1: true_prob = true_prob / 100.0 # Normalize percentage
                                
                                if true_prob > 0:
                                    # Standardized Formula: Prob Diff
                                    implied = 1.0 / u_odds if u_odds > 0 else 0
                                    calc_edge = true_prob - implied
                                    
                                    edge_color = "#10B981" if calc_edge > 0 else "#EF4444"
                                    st.markdown(f"<div style='margin-bottom: 8px; font-size: 13px;'>Win Prob: <b style='color: #E2E8F0'>{true_prob*100:.1f}%</b> | Edge: <b style='color: {edge_color}'>{calc_edge*100:.1f}%</b></div>", unsafe_allow_html=True)

                                if st.button("Confirm", key=f"p_btn_{row['event_id']}", use_container_width=True):
                                    confirm_bet(row['event_id'], u_odds, u_stake)

        # --- TAB 4: ADMIN & ANALYTICS ---
        with tab4:
            st.markdown("### 🛠️ Admin Headquarters")
            if check_auth("Admin Tools"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Maintenance**")
                    if st.button("🧹 Clear Ghost Bets", use_container_width=True):
                         surgical_cleanup()
                with c2:
                    st.markdown("**Bankroll**")
                    cur_br = get_starting_bankroll()
                    nbr = st.number_input("Bankroll ($)", value=cur_br, step=10.0)
                    if nbr != cur_br:
                        if st.button("💾 Save", key="s_br"): update_bankroll(nbr)
                
                st.divider()
                st.markdown("### 📈 Performance Analytics")
                if not df_settled.empty:
                    wins = len(df_settled[df_settled['outcome'] == 'WON'])
                    total = len(df_settled)
                    win_rate = (wins/total)*100 if total > 0 else 0
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Bets", total)
                    c2.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    # Simple PnL Calc
                    profit = 0
                    for _, r in df_settled.iterrows():
                        if r['outcome'] == 'WON': profit += r['Stake_Val'] * (r['Dec_Odds'] - 1)
                        elif r['outcome'] == 'LOST': profit -= r['Stake_Val']
                    
                    c3.metric("Net Profit", f"${profit:.2f}")
                    
                    st.dataframe(df_settled[['Date','Sport','Event','Selection','outcome']], use_container_width=True, hide_index=True)
                else:
                    st.info("No settled bets.")

        # --- TAB 5: TRUTH (CALIBRATION) ---
        with tab5:
            st.markdown("### 👁️ Model Truth (Calibration Phase 2)")
            st.markdown("This tab tracks the *actual* win rate of the model's probability buckets.")
            
            conn = get_db()
            if conn:
                try:
                    c_df = pd.read_sql("""
                        SELECT c.bucket, i.outcome 
                        FROM calibration_log c 
                        JOIN intelligence_log i ON c.event_id = i.event_id 
                        WHERE i.outcome IN ('WIN', 'LOSS')
                    """, conn)
                    
                    if not c_df.empty:
                        c_df['is_win'] = c_df['outcome'].apply(lambda x: 1 if x == 'WIN' else 0)
                        
                        stats = c_df.groupby('bucket')['is_win'].agg(['count', 'mean']).reset_index()
                        stats.columns = ['Bucket', 'Bets', 'WinRate']
                        stats['WinRate%'] = (stats['WinRate'] * 100).round(1)
                        
                        st.dataframe(stats, hide_index=True)
                        
                        stats['Expected'] = stats['Bucket'].apply(lambda x: float(x.split('-')[0]) + 2.5)
                        chart_data = stats[['Expected', 'WinRate%']].set_index('Expected')
                        st.line_chart(chart_data)
                        
                        st.success(f"Tracking {len(c_df)} settled predictions.")
                    else:
                        st.info("📉 No settled bets found in Calibration Log yet. Data will populate as games finish.")
                        try:
                            pending = pd.read_sql("SELECT count(*) FROM calibration_log", conn).iloc[0,0]
                            st.caption(f"Pending Predictions Logged: {pending}")
                        except:
                            pass
                except Exception as e:
                    st.error(f"Error loading calibration data: {e}")
                finally:
                    conn.close()

    except Exception as e:
        st.error(f"Dashboard Error: {e}")
    finally:
        if conn:
            conn.close()

