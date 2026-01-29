
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
# from processing.parlay import generate_parlays (REMOVED)
import re
from db.connection import get_db, get_last_update_time, get_starting_bankroll, update_bankroll, surgical_cleanup
from db.queries import (
    fetch_pending_opportunities, fetch_settled_bets, fetch_distinct_sports, 
    update_user_bet, cancel_user_bet, save_parlay
)

def check_auth(module_name="Admin"):
    """Simple authorization check."""
    # 1. Check if already authorized in session
    if st.session_state.get(f'auth_{module_name}', False):
        return True

    # 2. Render Login Form
    with st.expander(f"🔐 Authenticate: {module_name}", expanded=True):
        password = st.text_input("Admin Password", type="password", key=f"pw_{module_name}")
        if st.button("Unlock", key=f"btn_unlock_{module_name}"):
            # Check against Env
            admin_pw = os.getenv("ADMIN_PASSWORD", "admin123") # Default only if env missing
            if password == admin_pw:
                st.session_state[f'auth_{module_name}'] = True
                st.success("Unlocked.")
                st.rerun()
            else:
                st.error("Invalid Password")
    
    return False


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
        rows = update_user_bet(conn, event_id, float(odds), float(stake))
        print(f"   ✅ [DASHBOARD] Rows affected: {rows}", flush=True)
        
        if rows > 0:
            st.session_state['toast_msg'] = (f"✅ Tracked bet {event_id}", "success")
        else:
            st.session_state['toast_msg'] = (f"⚠️ Event ID {event_id} not found.", "warning")
            
    except Exception as e:
        print(f"❌ [DASHBOARD] Error: {e}", flush=True)
        st.session_state['toast_msg'] = (f"❌ Error tracking bet: {e}", "error")
    finally:
        conn.close()

# ... (skip to cancel_bet_db)

def cancel_bet_db(event_id):
    print(f"🔥 [DASHBOARD] Callback Triggered: Cancel {event_id}", flush=True)
    conn = get_db()
    
    if not conn:
        print("❌ [DASHBOARD] DB Connection Failed in Callback", flush=True)
        st.session_state['toast_msg'] = ("❌ DB Connection Failed", "error")
        return

    try:
        rows = cancel_user_bet(conn, event_id)
        print(f"   ✅ [DASHBOARD] Rows affected: {rows}", flush=True)
        
        if rows > 0:
            st.session_state['toast_msg'] = (f"✅ Cancelled bet {event_id}", "success")
        else:
            st.session_state['toast_msg'] = (f"⚠️ Event ID {event_id} not found or already cancelled.", "warning")
            
    except Exception as e:
        print(f"❌ [DASHBOARD] Error: {e}", flush=True)
        st.session_state['toast_msg'] = (f"❌ Error cancelling bet: {e}", "error")
    finally:
        conn.close()


# confirm_parlay function removed (Logic deprecated)

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
    all_sports = sorted(fetch_distinct_sports(conn))
    # Clean up sport names for display
    display_sports = [s.replace('basketball_', '').replace('americanfootball_', '').replace('icehockey_', '').replace('soccer_', '').upper() for s in all_sports]
    
    selected_sports = st.multiselect("Filter Sport", display_sports, default=[])

    mobile_view = st.checkbox("📱 Mobile View", value=False)
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
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
            
        # Fetch Data (Cached to prevent DB spam on filter change)
        @st.cache_data(ttl=30, show_spinner=False)
        def get_cached_dashboard_data():
             p = fetch_pending_opportunities(conn, limit=1000) # Bumped limit slightly since cached
             s = fetch_settled_bets(conn)
             return p, s

        df_p, df_s = get_cached_dashboard_data()

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
            
            # --- GLOBAL TIME FILTER (ALWAYS ON) ---
            # 1. No Past Games (Live/Started)
            # 2. No Distant Future (> 36 Hours)
            now_est = pd.Timestamp.now(tz='US/Eastern')
            limit_est = now_est + pd.Timedelta(hours=36)
            
            # Filter Logic:
            # Keep if (User Bet == TRUE) OR (Kickoff > Now AND Kickoff <= Limit)
            # We want to keep User Bets visible even if started? 
            # User said "filter out selections that are past their start time. Always, no exceptions"
            # BUT usually Portfolio needs to show active bets.
            # Assuming "Selections" means "Recommendations". Portfolio is "My Bets".
            # Let's apply strict filter for Recommendations. Portfolio handles its own display.
            
            # Actually, `clean_df` is applied to df_p (Pending) and df_s (Settled).
            # Settled shouldn't be filtered by time.
            # Pending includes User Bets.
            
            # Let's just return the df here and apply the filter strictly on df_pending below
            # OR map a boolean mask.
            
            mask_future = (df['kickoff'] > now_est) & (df['kickoff'] <= limit_est)
            mask_user = (df.get('user_bet', False) == True)
            
            # STRICT RULE: Dashboard only shows FUTURE opportunities.
            # However, for "Active Portfolio" (Tab 2), we MUST show started games that are pending result.
            # The User said: "automatically filter out selections that are past their start time" -> usually implies the Betting Feed.
            # "The NHL props are now on the dashboard, but they persist after start time." -> Feed.
            
            # Safe Approach: Filter df_pending to exclude NON-USER-BET rows that are past start time.
            # Keep User Bets regardless of time (so they show in Portfolio).
            
            df = df[mask_future | mask_user].copy()
            
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
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Live Edge Feed", "💼 Active Portfolio", "admin_tools", "👁️ Truth (Calibration)", "📈 Performance"])
        # Note: Renaming tabs to match user expectation: "Admin Tools" was in list.
        # Original: ["⚡ Live Edge Feed", "💼 Active Portfolio", "⚽ Player Prop Edges", "🛠️ Admin & Analytics", "👁️ Truth (Calibration)", "📈 Performance"]
        # Removed "Player Prop Edges" instead of Parlay? wait. 
        # User said "Remove Parlay Builder".
        # Let's align with what was likely intended:
        # T1: Live Feed
        # T2: Portfolio
        # T3: Props? Or Admin?
        # Let's stick to safe structure:
        
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Live Edge Feed", "💼 Active Portfolio", "⚽ Player Props", "🛠️ Admin", "📈 Performance"])

        with tab1:
                st.markdown("### ⚡ Top 15 Opportunities")
                st.caption("Best value plays from every available sport, sorted by kickoff.")
                
                # Base Filter: Future Games + Not Bet + Edge 3-15% + NOT PROPS + 36H LIMIT
                top_pool = df_pending[
                    (df_pending['user_bet'] == False) & 
                    (df_pending['kickoff'] > now_est) &
                    (df_pending['kickoff'] <= (now_est + pd.Timedelta(hours=36))) &
                    (df_pending['Edge_Val'] >= 0.03) & 
                    (df_pending['Edge_Val'] <= 0.15) &
                    (~df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_')))
                ].copy()

# ...

                sharp_pool = df_pending[
                    (df_pending['user_bet'] == False) & 
                    (df_pending['kickoff'] > now_est) &
                    (df_pending['kickoff'] <= (now_est + pd.Timedelta(hours=36))) &
                    (pd.to_numeric(df_pending['sharp_score'], errors='coerce') >= 70)
                ].copy()

# ...


# ...

                # Filter out started games + 36H Limit
                prop_df = df_pending[
                    (df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_'))) &
                    (df_pending['kickoff'] > now_est) &
                    (df_pending['kickoff'] <= (now_est + pd.Timedelta(hours=36)))
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
                        # Logic for Integrated Sharp Label
                        sharp_score = pd.to_numeric(row.get('sharp_score'), errors='coerce')
                        sharp_suffix = ""
                        if sharp_score >= 70:
                                sharp_suffix = "<span style='color: #F59E0B; font-size: 10px; margin-left: 4px;'>🔥 SHARP</span>"
                        elif sharp_score >= 45:
                                sharp_suffix = "<span style='color: #60A5FA; font-size: 10px; margin-left: 4px;'>🔵 LEAN</span>"

                        # Logic for Ticket/Money %
                        t_pct = pd.to_numeric(row.get('ticket_pct'), errors='coerce')
                        m_pct = pd.to_numeric(row.get('money_pct'), errors='coerce')
                        sharp_data_line = ""
                        if pd.notna(t_pct) and pd.notna(m_pct) and (t_pct > 0 or m_pct > 0):
                             sharp_data_line = f"<div style='color: #FCD34D; font-size: 11px; margin-top: 4px; font-family: monospace;'>🎟️ {int(t_pct)}% | 💰 {int(m_pct)}%</div>"
                        else:
                             sharp_data_line = "<div style='color: #475569; font-size: 10px; margin-top: 4px;'>No Signal</div>"

                        with t_cols[idx % 3]:
                            st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #F59E0B; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                                <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                    <div>
                                        <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                        <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']} {sharp_suffix}</div>
                                    </div>
                                    {sharp_data_line}
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
                st.info("ℹ️ **Explainer**: These plays feature high Sharp Scores (>= 70).")
                
                sharp_pool = df_pending[
                        (df_pending['user_bet'] == False) & 
                        (df_pending['kickoff'] > now_est) &
                        (pd.to_numeric(df_pending['sharp_score'], errors='coerce') >= 70)
                    ].copy()
                
    
                if not sharp_pool.empty:
                    sharp_pool = sharp_pool.sort_values('kickoff', ascending=True)
                    for idx, (_, row) in enumerate(sharp_pool.iterrows()):
                         
                         # Integrated Label
                         sharp_suffix = "<span style='color: #F59E0B; font-size: 10px; margin-left: 4px;'>🔥 SHARP</span>"
                         
                         # Logic for Ticket/Money %
                         t_pct = pd.to_numeric(row.get('ticket_pct'), errors='coerce')
                         m_pct = pd.to_numeric(row.get('money_pct'), errors='coerce')
                         sharp_data_line = ""
                         if pd.notna(t_pct) and pd.notna(m_pct) and (t_pct > 0 or m_pct > 0):
                             sharp_data_line = f"<div style='color: #FCD34D; font-size: 11px; margin-top: 4px; font-family: monospace;'>🎟️ {int(t_pct)}% | 💰 {int(m_pct)}%</div>"
                         else:
                             sharp_data_line = "<div style='color: #475569; font-size: 10px; margin-top: 4px;'>No Signal</div>"

                         st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #60A5FA; margin-bottom: 12px; opacity: 0.9;'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                                <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                    <div>
                                        <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                        <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']} {sharp_suffix}</div>
                                    </div>
                                    {sharp_data_line}
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
                    (~df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_'))) &
                    (~df_pending['event_id'].isin(displayed_ids))
                ].copy()

                if not general_pool.empty:
                    general_pool = general_pool.sort_values('kickoff', ascending=True)
                    g_cols = st.columns(2) # 2 per row
                    for idx, (_, row) in enumerate(general_pool.iterrows()):
                        # Logic for Integrated Sharp Label
                        sharp_score = pd.to_numeric(row.get('sharp_score'), errors='coerce')
                        sharp_suffix = ""
                        if sharp_score >= 70:
                             sharp_suffix = "<span style='color: #F59E0B; font-size: 10px; margin-left: 4px;'>🔥 SHARP</span>"
                        elif sharp_score >= 45:
                             sharp_suffix = "<span style='color: #60A5FA; font-size: 10px; margin-left: 4px;'>🔵 LEAN</span>"

                        # Logic for Ticket/Money %
                        t_pct = pd.to_numeric(row.get('ticket_pct'), errors='coerce')
                        m_pct = pd.to_numeric(row.get('money_pct'), errors='coerce')
                        sharp_data_line = ""
                        if pd.notna(t_pct) and pd.notna(m_pct) and (t_pct > 0 or m_pct > 0):
                             sharp_data_line = f"<div style='color: #FCD34D; font-size: 11px; margin-top: 4px; font-family: monospace;'>🎟️ {int(t_pct)}% | 💰 {int(m_pct)}%</div>"
                        else:
                             sharp_data_line = "<div style='color: #475569; font-size: 10px; margin-top: 4px;'>No Signal</div>"

                        with g_cols[idx % 2]:
                            st.markdown(clean_html(f"""
                            <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #10B981; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                                <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                    <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                                </div>
                                <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                                <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                    <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                    <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                                </div>
                                <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                    <div>
                                        <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                        <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']} {sharp_suffix}</div>
                                    </div>
                                    {sharp_data_line}
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
                (df_pending['event_id'].astype(str).str.startswith(('PROP_', 'NHL_'))) &
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
                    # Logic for Integrated Sharp Label
                    sharp_score = pd.to_numeric(row.get('sharp_score'), errors='coerce')
                    sharp_suffix = ""
                    if sharp_score >= 70:
                            sharp_suffix = "<span style='color: #F59E0B; font-size: 10px; margin-left: 4px;'>🔥 SHARP</span>"
                    elif sharp_score >= 45:
                            sharp_suffix = "<span style='color: #60A5FA; font-size: 10px; margin-left: 4px;'>🔵 LEAN</span>"

                    # Logic for Ticket/Money %
                    t_pct = pd.to_numeric(row.get('ticket_pct'), errors='coerce')
                    m_pct = pd.to_numeric(row.get('money_pct'), errors='coerce')
                    sharp_data_line = ""
                    if pd.notna(t_pct) and pd.notna(m_pct) and (t_pct > 0 or m_pct > 0):
                            sharp_data_line = f"<div style='color: #FCD34D; font-size: 11px; margin-top: 4px; font-family: monospace;'>🎟️ {int(t_pct)}% | 💰 {int(m_pct)}%</div>"
                    else:
                            sharp_data_line = "<div style='color: #475569; font-size: 10px; margin-top: 4px;'>No Signal</div>"

                    with pcols[i % 3]:
                        st.markdown(clean_html(f"""
                        <div style='background: #1E293B; padding: 12px; border-radius: 8px; border-left: 4px solid #3B82F6; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                            <div style='display: flex; justify-content: space-between; align-items: start; margin-bottom: 4px;'>
                                <span style='color: #94A3B8; font-size: 11px; font-weight: 600;'>{row['Sport']} • {row['Kickoff']}</span>
                            </div>
                            <div style='color: #F8FAFC; font-size: 13px; font-weight: 700; margin-bottom: 6px; line-height: 1.2;'>{row['Event']}</div>
                            <div style='display: flex; justify-content: space-between; align-items: center; background: #334155; padding: 6px; border-radius: 6px;'>
                                <div style='color: #60A5FA; font-weight: 700; font-size: 14px;'>{row['Selection']}</div>
                                <div style='color: #F8FAFC; font-size: 13px;'>@{row['Dec_Odds']:.2f}</div>
                            </div>
                            <div style='display: flex; justify-content: space-between; margin-top: 8px; padding-top: 4px; border-top: 1px solid #334155;'>
                                <div>
                                    <div style='color: #94A3B8; font-size: 10px;'>EDGE</div>
                                    <div style='color: #10B981; font-weight: 700; font-size: 14px;'>{row['Edge']} {sharp_suffix}</div>
                                </div>
                                <!-- STAKE REMOVED -->
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
                        WHERE i.outcome IN ('WON', 'LOST')
                    """, conn)
                    
                    if not c_df.empty:
                        c_df['is_win'] = c_df['outcome'].apply(lambda x: 1 if x == 'WON' else 0)
                        
                        stats = c_df.groupby('bucket')['is_win'].agg(['count', 'sum', 'mean']).reset_index()
                        stats.columns = ['Bucket', 'Bets', 'Wins', 'WinRate']
                        stats['Win%'] = (stats['WinRate'] * 100).round(1)
                        stats['Win%'] = stats['Win%'].apply(lambda x: f"{x}%")
                        
                        # Display Clarity
                        st.dataframe(stats[['Bucket', 'Bets', 'Wins', 'Win%']], hide_index=True, use_container_width=True)
                        
                        stats['Expected'] = stats['Bucket'].apply(lambda x: float(x.split('-')[0]) + 2.5)
                        chart_data = stats[['Expected', 'WinRate']].set_index('Expected')
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

        # --- TAB 6: PERFORMANCE ---
        with tab6:
            # Custom CSS for Financial Terminal Look
            st.markdown("""
            <style>
                /* KPI Card Styling */
                .fin-card {
                    background: #0F172A;
                    border: 1px solid #1E293B;
                    border-left: 4px solid #3B82F6;
                    border-radius: 8px;
                    padding: 16px 20px;
                    margin-bottom: 12px;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                }
                .fin-label {
                    color: #94A3B8;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    font-weight: 600;
                }
                .fin-value {
                    color: #F8FAFC;
                    font-size: 24px;
                    font-weight: 700;
                    margin-top: 6px;
                    font-family: 'SF Mono', 'Menlo', 'Monaco', 'Courier New', monospace;
                }
                
                /* Filter Styling */
                div[data-testid="stRadio"] > label {
                    display: none;
                }
                div[role="radiogroup"] {
                    background-color: #1E293B;
                    padding: 4px;
                    border-radius: 8px;
                    border: 1px solid #334155;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Header + Controls
            c_head1, c_head2 = st.columns([3, 1])
            with c_head1:
                st.markdown("### 📈 Performance Analysis")
            with c_head2:
                # Native "Pills" Look via Radio
                time_filter = st.radio(
                    "Timeframe", 
                    ["All Time", "30D", "7D"], 
                    horizontal=True,
                    label_visibility="collapsed"
                )

            if not df_settled.empty:
                perf_df = df_settled.copy()
                
                # --- DATA FILTERING ---
                now = pd.Timestamp.now(tz='US/Eastern')
                if time_filter == "7D":
                    cutoff = now - pd.Timedelta(days=7)
                    perf_df = perf_df[perf_df['kickoff'] >= cutoff]
                elif time_filter == "30D":
                    cutoff = now - pd.Timedelta(days=30)
                    perf_df = perf_df[perf_df['kickoff'] >= cutoff]
                
                if perf_df.empty:
                    st.warning(f"No settled bets in {time_filter}.")
                else:
                    # --- CALCULATION ENGINE ---
                    def calc_pnl(row):
                        outcome = str(row['outcome']).upper()
                        try: 
                            stake = float(row['Stake_Val'])
                            odds = float(row['Dec_Odds'])
                        except: return 0.0

                        if outcome == 'WON': return stake * (odds - 1)
                        elif outcome == 'LOST': return -stake
                        return 0.0
                        
                    perf_df['Profit'] = perf_df.apply(calc_pnl, axis=1)

                    # --- SPORT MAPPER ---
                    def map_sport_icon(s):
                        s = str(s).upper()
                        if 'NBA' in s or 'NCAAB' in s: return f"🏀 {s}"
                        if 'NHL' in s: return f"🏒 {s}"
                        if 'NFL' in s or 'CFL' in s: return f"🏈 {s}"
                        if 'MLB' in s: return f"⚾ {s}"
                        if 'SOCCER' in s or 'LIGA' in s or 'EPL' in s: return f"⚽ {s}"
                        if 'TENNIS' in s: return f"🎾 {s}"
                        if 'UFC' in s or 'MMA' in s: return f"🥊 {s}"
                        return f"🏅 {s}"

                    perf_df['Sport_Display'] = perf_df['Sport'].apply(map_sport_icon)

                    # --- METRICS SECTION ---
                    total_profit = perf_df['Profit'].sum()
                    total_stake = perf_df['Stake_Val'].sum()
                    roi = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
                    
                    # Layout: Metrics
                    k1, k2, k3, k4 = st.columns(4)
                    
                    p_color = "#10B981" if total_profit >= 0 else "#EF4444"
                    r_color = "#10B981" if roi >= 0 else "#EF4444"

                    with k1:
                        st.markdown(f"""
                        <div class="fin-card">
                            <div class="fin-label">Total Profit</div>
                            <div class="fin-value" style="color: {p_color}">${total_profit:,.2f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with k2:
                        st.markdown(f"""
                        <div class="fin-card">
                            <div class="fin-label">Total Volume</div>
                            <div class="fin-value">${total_stake:,.0f}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with k3:
                        st.markdown(f"""
                        <div class="fin-card">
                            <div class="fin-label">ROI</div>
                            <div class="fin-value" style="color: {r_color}">{roi:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                    with k4:
                        st.markdown(f"""
                        <div class="fin-card">
                            <div class="fin-label">Total Bets</div>
                            <div class="fin-value">{len(perf_df)}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # --- TABLE ENGINE ---
                    sport_stats = perf_df.groupby('Sport_Display').agg({
                        'Profit': 'sum',
                        'Stake_Val': 'sum',
                        'outcome': 'count',
                        'Dec_Odds': 'mean'
                    }).reset_index()

                    sport_stats['ROI'] = (sport_stats['Profit'] / sport_stats['Stake_Val']).fillna(0)
                    sport_stats['AvgOdds'] = sport_stats['Dec_Odds']
                    
                    # Sort by Profit (Waterfall Logic)
                    sport_stats = sport_stats.sort_values('Profit', ascending=False)
                    
                    # --- PANDAS STYLER (Bloomberg Polish) ---
                    display_df = sport_stats[['Sport_Display', 'outcome', 'Stake_Val', 'Profit', 'ROI', 'AvgOdds']].copy()
                    
                    def color_profit_text(val):
                        if val > 0: return 'color: #34D399'
                        if val < 0: return 'color: #F87171'
                        return 'color: #94A3B8'

                    styler = display_df.style\
                        .background_gradient(subset=['ROI'], cmap='RdYlGn', vmin=-1.5, vmax=1.5, text_color_threshold=0.5)\
                        .applymap(color_profit_text, subset=['Profit'])\
                        .format({
                            'Profit': "${:,.2f}",
                            'ROI': "{:.1%}",
                            'AvgOdds': "{:.2f}",
                            'Stake_Val': "${:,.0f}"
                        })\
                        .set_properties(**{
                            'background-color': '#1E293B',
                            'color': '#F8FAFC',
                            'border-color': '#334155'
                        })\
                        .set_table_styles([
                            {'selector': 'th', 'props': [('background-color', '#0F172A'), ('color', '#94A3B8'), ('font-weight', 'bold'), ('border-bottom', '1px solid #334155')]},
                            {'selector': 'tr:hover', 'props': [('background-color', '#334155')]}
                        ])
                    
                    # Inject Custom Headers Styles (Pandas Styler Hooks are limited in Streamlit, but we try)
                    # Note: st.dataframe inherits theme. We focus on column config.

                    st.dataframe(
                        styler,
                        column_config={
                            "Sport_Display": st.column_config.TextColumn("Sport", width=None),
                            "outcome": st.column_config.NumberColumn("Bets", format="%d"),
                            "Stake_Val": st.column_config.ProgressColumn(
                                "Volume", 
                                format="$%.0f", 
                                min_value=0, 
                                max_value=float(sport_stats['Stake_Val'].max())
                            ),
                            "Profit": "Profit ($)",
                            "ROI": "ROI (%)",
                            "AvgOdds": "Avg Odds"
                        },
                        hide_index=True,
                        use_container_width=True,
                        height=400
                    )

                    # --- CHART: WATERFALL (Altair) ---
                    import altair as alt
                    st.subheader("Profit Distribution")
                    
                    base = alt.Chart(sport_stats).encode(
                        x=alt.X('Sport_Display', sort=None, axis=alt.Axis(labels=True, title=None, labelAngle=-45, grid=False, labelColor='#94A3B8')), 
                        y=alt.Y('Profit', axis=None), 
                    )
                    
                    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                        color=alt.condition(
                            alt.datum.Profit > 0,
                            alt.value('#34D399'), 
                            alt.value('#F87171')
                        ),
                        tooltip=['Sport_Display', 'outcome', alt.Tooltip('Profit', format='$.2f'), alt.Tooltip('ROI', format='.1%')]
                    )
                    
                    text = base.mark_text(
                        align='center',
                        baseline='bottom',
                        dy=-5 
                    ).encode(
                        text=alt.Text('Profit', format='$.0f'),
                        color=alt.value('#E2E8F0')
                    )
                    
                    # Dark Mode Chart Config
                    chart = (bars + text).configure_axis(
                        grid=False, 
                        domain=False
                    ).configure_view(
                        strokeOpacity=0
                    ).properties(
                        background='transparent'
                    )
                    
                    st.altair_chart(chart, use_container_width=True)

            else:
                st.info("No settled bets to analyze yet.")

    except Exception as e:
        st.error(f"Dashboard Error: {e}")
    finally:
        if conn:
            conn.close()

