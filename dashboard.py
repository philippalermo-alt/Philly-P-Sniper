import streamlit as st
import pandas as pd
import psycopg2
import os
import requests
from datetime import datetime
import difflib
from backtesting import analyze_by_edge_bucket

# 🎨 Modern Page Configuration
st.set_page_config(
    page_title="Philly P Sniper",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# 🎨 Custom CSS for Modern Look
st.markdown("""
<style>
    /* Main background - Clean light blue-gray */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    /* Headers */
    h1 {
        color: #1a202c;
        font-weight: 700;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    h2, h3 {
        color: #2d3748;
        font-weight: 600;
    }

    /* All text elements */
    p, label, span, div {
        color: #1a202c;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
        color: #1a202c;
    }

    [data-testid="stMetricLabel"] {
        color: #4a5568;
    }

    /* Cards with borders */
    [data-testid="stHorizontalBlock"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #ffffff;
        padding: 8px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #f7fafc;
        border-radius: 8px;
        color: #4a5568;
        font-weight: 600;
        font-size: 16px;
        padding: 0 24px;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f7fafc 100%);
        border-right: 1px solid #e2e8f0;
    }

    [data-testid="stSidebar"] * {
        color: #1a202c;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #2d3748;
    }

    /* Input fields */
    .stNumberInput > div > div > input {
        background-color: #ffffff;
        color: #1a202c;
        border: 1px solid #cbd5e0;
        border-radius: 6px;
    }

    .stSlider > div > div > div {
        color: #1a202c;
    }

    /* Dividers */
    hr {
        margin: 30px 0;
        border-color: #cbd5e0;
    }

    /* Containers */
    .element-container {
        margin-bottom: 10px;
    }

    /* Captions */
    .st-emotion-cache-16idsys p {
        color: #718096;
        font-size: 14px;
    }

    /* Success/Info/Warning boxes */
    .stSuccess {
        background-color: #f0fdf4;
        border-left: 4px solid #10b981;
        border-radius: 8px;
        color: #065f46;
    }

    .stInfo {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        color: #1e40af;
    }

    .stWarning {
        background-color: #fffbeb;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
        color: #92400e;
    }

    .stError {
        background-color: #fef2f2;
        border-left: 4px solid #ef4444;
        border-radius: 8px;
        color: #991b1b;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #f7fafc;
        border-radius: 8px;
        font-weight: 600;
        color: #2d3748;
    }

    /* Text areas */
    textarea {
        background-color: #ffffff;
        color: #1a202c;
        border: 1px solid #cbd5e0;
        border-radius: 6px;
    }

    /* Select boxes */
    .stSelectbox > div > div {
        background-color: #ffffff;
        color: #1a202c;
    }
</style>
""", unsafe_allow_html=True)

# --- Database Connection Setup ---
@st.cache_resource(ttl=3600)
def init_connection():
    try:
        return psycopg2.connect(os.getenv('DATABASE_URL'), sslmode='prefer')
    except Exception as e:
        st.error(f"❌ DB Connection Failed: {e}")
        return None

def get_db():
    conn = init_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except:
        st.cache_resource.clear()
        return init_connection()

# --- Security & Cleanup Logic ---
def surgical_cleanup():
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM intelligence_log WHERE outcome = 'PENDING' AND user_bet = FALSE;")
            conn.commit()
            st.sidebar.success(f"🧹 Cleaned {cur.rowcount} ghost bets!")
            cur.close()
            conn.close()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Cleanup failed: {e}")

# --- UI Helpers ---
def get_sharp_badge(row):
    """Returns modern badge HTML for sharp score"""
    raw_score = row.get("sharp_score")
    m, t = row.get("money_pct"), row.get("ticket_pct")

    if pd.isna(raw_score) or raw_score is None:
        return '<span style="background: #6b7280; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">⚪ NO DATA</span>'

    try:
        score = float(raw_score)
        if pd.notnull(m) and pd.notnull(t):
            if float(m) <= float(t):
                return f'<span style="background: #6b7280; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">🤡 PUBLIC ({int(round(score))})</span>'

        s = int(round(score))
        if s >= 75:
            return f'<span style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">🔥 SHARP ({s})</span>'
        if s >= 50:
            return f'<span style="background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">🧠 SHARP ({s})</span>'
        if s >= 25:
            return f'<span style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">🧠 LEAN ({s})</span>'

        return f'<span style="background: #6b7280; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">⚪ NO SIGNAL ({s})</span>'
    except:
        return '<span style="background: #ef4444; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600;">⚠️ ERROR</span>'

def get_starting_bankroll():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
        row = cur.fetchone()
        return float(row[0]) if row else 451.16
    except:
        return 451.16

def update_bankroll(val):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(val),))
        conn.commit()
        st.rerun()
    except Exception as e:
        st.error(f"Failed to update: {e}")

def confirm_bet(event_id, current_status, user_odds=None, user_stake=None):
    conn = get_db()
    try:
        cur = conn.cursor()
        new_status = not current_status
        if new_status and user_odds is not None:
            cur.execute("""
                UPDATE intelligence_log
                SET user_bet = %s, user_odds = %s, user_stake = %s
                WHERE event_id = %s
            """, (new_status, float(user_odds), float(user_stake), event_id))
        else:
            cur.execute("UPDATE intelligence_log SET user_bet = %s WHERE event_id = %s", (new_status, event_id))

        conn.commit()
        cur.close()
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")

@st.cache_data(ttl=60)
def fetch_live_games(sport_keys):
    """
    Fetch live scores from ESPN's public hidden API (Free).
    """
    games = []
    logs = []
    
    unique_sports = set(sport_keys)
    
    # Map internal keys to ESPN API paths
    # Format: {sport}/{league}
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
        'soccer_uefa_champs_league': 'soccer/uefa.champions',
        'CHAMPIONS': 'soccer/uefa.champions'
    }

    processed_paths = set()

    # FORCE US/EASTERN DATE logic
    # Heroku is UTC. If it is 2 AM UTC, it's 9 PM ET. We want "today" to be 9 PM ET.
    import pytz
    tz = pytz.timezone('US/Eastern')
    now_et = datetime.now(tz)
    # ESPN date param format: YYYYMMDD
    date_str = now_et.strftime('%Y%m%d')

    # Log keys for debugging
    logs.append(f"Keys: {list(unique_sports)}")

    for sport_key in unique_sports:
        espn_path = ESPN_MAP.get(sport_key)
        if not espn_path or espn_path in processed_paths:
            continue
            
        processed_paths.add(espn_path)

        try:
            url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_path}/scoreboard?dates={date_str}"
            
            # Use User-Agent to avoid generic bot blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            r = requests.get(url, headers=headers, timeout=5)
            
            if r.status_code == 200:
                res = r.json()
                events = res.get('events', [])
                logs.append(f"✅ {espn_path}: {len(events)} events (Date: {date_str})")
                
                for event in events:
                    # ESPN structure: events -> competitions[0] -> competitors
                    comp = event['competitions'][0]
                    status_detail = event.get('status', {}).get('type', {}).get('shortDetail', 'Scheduled')
                    is_complete = event.get('status', {}).get('type', {}).get('completed', False)
                    
                    # Teams
                    competitors = comp.get('competitors', [])
                    home_comp = next((c for c in competitors if c['homeAway'] == 'home'), {})
                    away_comp = next((c for c in competitors if c['homeAway'] == 'away'), {})
                    
                    h_name = home_comp.get('team', {}).get('displayName', 'Home')
                    a_name = away_comp.get('team', {}).get('displayName', 'Away')
                    h_score = home_comp.get('score', '0')
                    a_score = away_comp.get('score', '0')
                    
                    # Formatting: "Q3 4:21" or "Final"
                    # status_icon = "🏁" if is_complete else "🔴"
                    
                    # Normalize names for matching logic (remove rank numbers which ESPN adds sometimes)
                    # For now, pass raw names. Fuzzy match in UI handles the rest.
                    
                    games.append({
                        'home': h_name,
                        'away': a_name,
                        'score': f"{status_detail}: {a_name} {a_score} - {h_name} {h_score}",
                        'commence': event.get('date') # ISO string
                    })
            else:
                logs.append(f"⚠️ {espn_path}: {r.status_code}")
        except Exception as e:
            logs.append(f"❌ {sport_key}: {e}")

    return games, logs

# --- Header ---
col1, col2, col3 = st.columns([2, 3, 2])
with col2:
    st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🎯 Philly P Sniper</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #718096; font-size: 16px; margin-top: 0; font-weight: 500;'>Advanced Betting Intelligence Platform</p>", unsafe_allow_html=True)

st.markdown("---")

# --- Sidebar ---
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    with st.expander("🔐 Admin Controls", expanded=False):
        pw_input = st.text_input("Admin Key", type="password", help="Enter key to enable admin functions")
        correct_pw = os.getenv("DASHBOARD_PASSWORD", "default_secret")

        st.markdown("##### Maintenance")
        if st.button("🧹 Clear Ghost Bets", use_container_width=True):
            if pw_input == correct_pw:
                surgical_cleanup()
            else:
                st.error("❌ Invalid Admin Key")

        st.divider()
        st.markdown("##### Bankroll Settings")
        current_br = get_starting_bankroll()
        new_br = st.number_input("Starting Bankroll ($)", value=current_br, step=10.0)
        if new_br != current_br:
            if st.button("💾 Save Bankroll", use_container_width=True):
                if pw_input == correct_pw:
                    update_bankroll(new_br)
                else:
                    st.error("❌ Invalid Admin Key")

    st.divider()
    st.markdown("### 🎛️ Filters")
    sharp_filter = st.slider("Min Sharp Score", 0, 100, 0, help="Filter opportunities by minimum sharp score")

    st.markdown("#### Edge Range")
    col1, col2 = st.columns(2)
    with col1:
        min_edge_filter = st.number_input("Min Edge %", min_value=0.0, max_value=100.0, value=0.0, step=0.5, help="Minimum edge percentage")
    with col2:
        max_edge_filter = st.number_input("Max Edge %", min_value=0.0, max_value=100.0, value=100.0, step=0.5, help="Maximum edge percentage")

    mobile_view = st.checkbox("📱 Mobile View", value=False, help="Optimized layout for mobile devices")

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.rerun()

    st.markdown("---")
    st.caption("💡 Tip: Use the tabs above to navigate between Live Sniper, Portfolio, and Performance views")

# --- Main Dashboard ---
conn = get_db()
if conn:
    try:
        df_p = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome = 'PENDING' AND timestamp >= NOW() - INTERVAL '24 HOURS' ORDER BY kickoff ASC LIMIT 500", conn)
        df_s = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome IN ('WON', 'LOST', 'PUSH') ORDER BY kickoff DESC", conn)
        conn.commit()

        def clean_df(df):
            if df.empty:
                return df
            df['kickoff'] = pd.to_datetime(df['kickoff']).dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert('US/Eastern')
            df['Date'] = df['kickoff'].dt.strftime('%Y-%m-%d')
            df['Kickoff'] = df['kickoff'].dt.strftime('%m-%d %H:%M')
            df['Sport'] = df['sport'].apply(lambda x: x.split('_')[-1].upper() if '_' in x else x)
            df['Event'] = df['teams']
            df['Selection'] = df['selection']

            def get_val(row, col_base):
                user_col = f"user_{col_base}"
                if user_col in row and pd.notnull(row[user_col]):
                    return float(row[user_col])
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

        # --- Sidebar Sport Filter ---
        if not df_pending.empty:
            all_sports = sorted(df_pending['Sport'].unique())
            with st.sidebar:
                st.markdown("#### 🏆 Sport Filter")
                selected_sports = st.multiselect("Select Sports", options=all_sports, default=all_sports, label_visibility="collapsed")
            
            if selected_sports:
                df_pending = df_pending[df_pending['Sport'].isin(selected_sports)]
            else:
                st.warning("⚠️ Please select at least one sport in the sidebar.")
                df_pending = df_pending[0:0] # Show empty if nothing selected

        tab1, tab2, tab3, tab4 = st.tabs(["🔫 Live Sniper Feed", "💼 Active Portfolio", "📈 Performance Analytics", "📋 Export Data"])

        with tab1:
            if not df_pending.empty:
                st.markdown("### 🎯 Top Opportunities")

                # Filter out games that have already started
                now_est = pd.Timestamp.now(tz='US/Eastern')
                df_upcoming = df_pending[df_pending['kickoff'] > now_est].copy()

                top_15 = df_upcoming.sort_values(by='Edge_Val', ascending=False).head(15) if not df_upcoming.empty else pd.DataFrame()

                if not top_15.empty:
                    if mobile_view:
                        for _, row in top_15.iterrows():
                            with st.container():
                                st.markdown(f"""
                                <div style='background: #ffffff; padding: 15px; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                                    <p style='color: #718096; font-size: 12px; margin: 0;'>{row['Sport']} • {row['Kickoff']}</p>
                                    <p style='color: #1a202c; font-size: 16px; font-weight: 600; margin: 5px 0;'>{row['Event']}</p>
                                    <p style='color: #667eea; font-size: 14px; margin: 5px 0; font-weight: 600;'>👉 {row['Selection']} @ {row['Dec_Odds']:.2f}</p>
                                    <p style='color: #10b981; font-size: 14px; margin: 5px 0; font-weight: 600;'>Edge: {row['Edge']} | Stake: {row['Stake']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        display_cols = ['Sport', 'Kickoff', 'Event', 'Selection', 'Dec_Odds', 'Edge', 'Stake']
                        st.dataframe(top_15[display_cols], use_container_width=True, hide_index=True, height=400)
                else:
                    st.info("📭 No upcoming opportunities available")
            else:
                st.info("📭 No opportunities available at the moment")

            st.markdown("---")
            st.markdown("### 🎰 All Available Plays")

            now_est = pd.Timestamp.now(tz='US/Eastern')
            sniper_df = df_pending[(df_pending['user_bet'] == False) & (df_pending['kickoff'] > now_est)].copy()

            # Apply sharp score filter
            if 'sharp_score' in sniper_df.columns:
                sniper_df = sniper_df[pd.to_numeric(sniper_df['sharp_score'], errors='coerce').fillna(0) >= sharp_filter]

            # Apply edge range filter
            if 'Edge_Val' in sniper_df.columns:
                edge_min = min_edge_filter / 100.0  # Convert percentage to decimal
                edge_max = max_edge_filter / 100.0
                sniper_df = sniper_df[(sniper_df['Edge_Val'] >= edge_min) & (sniper_df['Edge_Val'] <= edge_max)]

            if sniper_df.empty:
                st.info("🎯 No plays match your current filters")
            else:
                for index, row in sniper_df.iterrows():
                    badge = get_sharp_badge(row)

                    with st.container():
                        if mobile_view:
                            st.markdown(f"""
                            <div style='background: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
                                <p style='color: #718096; font-size: 13px; margin-bottom: 8px;'>{row['Sport']} • Kickoff: {row['Kickoff']}</p>
                                <h4 style='color: #1a202c; margin: 8px 0;'>{row['Event']}</h4>
                                <p style='color: #667eea; font-size: 16px; font-weight: 600; margin: 10px 0;'>👉 {row['Selection']} @ {row['Dec_Odds']:.2f}</p>
                                <div style='margin: 15px 0;'>
                                    <span style='color: #10b981; font-size: 14px; font-weight: 600; margin-right: 20px;'>Edge: {row['Edge']}</span>
                                    <span style='color: #f59e0b; font-size: 14px; font-weight: 600;'>Stake: {row['Stake']}</span>
                                </div>
                                <div style='margin-top: 12px;'>{badge}</div>
                            </div>
                            """, unsafe_allow_html=True)

                            with st.expander("✅ Track This Bet"):
                                u_odds = st.number_input("Your Odds", value=float(row['Dec_Odds']), key=f"uo_{row['event_id']}")
                                u_stake = st.number_input("Your Stake ($)", value=float(row['Stake_Val']), key=f"us_{row['event_id']}")
                                if st.button("Confirm & Track", key=f"btn_{row['event_id']}", use_container_width=True):
                                    confirm_bet(row['event_id'], row['user_bet'], u_odds, u_stake)
                        else:
                            cols = st.columns([1, 2.5, 2, 1, 1, 2, 1.5])
                            cols[0].markdown(f"**{row['Sport']}**")
                            cols[0].caption(row['Kickoff'])
                            cols[1].markdown(f"**{row['Event']}**")
                            cols[2].markdown(f"**{row['Selection']}**")
                            cols[2].caption(f"@ {row['Dec_Odds']:.2f}")
                            cols[3].metric("Edge", row['Edge'])
                            cols[4].metric("Stake", row['Stake'])
                            cols[5].markdown(badge, unsafe_allow_html=True)
                            if pd.notnull(row.get('money_pct')):
                                cols[5].caption(f"💰 {int(row['money_pct'])}% | 🎟️ {int(row['ticket_pct'])}%")

                            with cols[6]:
                                with st.popover("✅"):
                                    u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), key=f"d_uo_{row['event_id']}")
                                    u_stake = st.number_input("$", value=float(row['Stake_Val']), key=f"d_us_{row['event_id']}")
                                    if st.button("Track", key=f"d_btn_{row['event_id']}", use_container_width=True):
                                        confirm_bet(row['event_id'], row['user_bet'], u_odds, u_stake)

                        st.markdown("---")

        with tab2:
            @st.fragment(run_every=60)
            def render_active_portfolio(df_source):
                st.markdown("### 💼 Your Active Wagers")
                st.caption("🟢 Live Updates: Auto-refreshing via ESPN (Free)")
                
                my_bets = df_source[df_source['user_bet'] == True].copy()

                if my_bets.empty:
                    st.info("📭 No active bets in your portfolio")
                else:
                    sport_keys = my_bets['sport'].unique()
                    live_games, debug_logs = fetch_live_games(sport_keys)

                    with st.expander("🔍 Live Score Debug", expanded=False):
                        st.write(f"Updated: {datetime.now().strftime('%H:%M:%S')} | Games Found: {len(live_games)}")
                        st.write("Live Games List:")
                        st.json(live_games)
                        if debug_logs:
                            st.error("Errors:")
                            for l in debug_logs:
                                st.text(l)

                    def get_score(row):
                        event = row['Event'].replace(' @ ', ' vs ')
                        teams = event.split(' vs ')
                        if len(teams) < 2:
                            return "🕒 Upcoming"

                        t1, t2 = teams[0], teams[1]

                        for g in live_games:
                            h, a = g['home'], g['away']
                            t1_match = (t1 in h or h in t1) or (t1 in a or a in t1)
                            t2_match = (t2 in h or h in t2) or (t2 in a or a in t2)

                            if t1_match and t2_match:
                                return g['score']
                            
                            # Fallback: Fuzzy Match
                            # If direct substring failed, check similarity ratio
                            # Helpful for "Jackson St" vs "Jackson State"
                            ratio_t1_h = difflib.SequenceMatcher(None, t1, h).ratio()
                            ratio_t1_a = difflib.SequenceMatcher(None, t1, a).ratio()
                            
                            ratio_t2_h = difflib.SequenceMatcher(None, t2, h).ratio()
                            ratio_t2_a = difflib.SequenceMatcher(None, t2, a).ratio()

                            # Threshold 0.6 is generous but safe given we are matching *both* teams
                            match_t1 = max(ratio_t1_h, ratio_t1_a) > 0.6
                            match_t2 = max(ratio_t2_h, ratio_t2_a) > 0.6

                            if match_t1 and match_t2:
                                return g['score']
                        
                        # DEBUG: If no match, maybe log why?
                        # This would flood the UI so we keep it simple, but we can verify the 'live_games' list in the expander above.
                        
                        return "🕒 Upcoming"

                    my_bets['Live Score'] = my_bets.apply(get_score, axis=1)

                    st.dataframe(
                        my_bets[['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Live Score', 'Dec_Odds', 'Stake']],
                        use_container_width=True,
                        hide_index=True,
                        height=400,
                        column_config={
                            "Live Score": st.column_config.TextColumn(
                                "Live Score",
                                help="Updates every 60s via ESPN",
                                width="medium"
                            )
                        }
                    )
            
            # Call the fragment
            render_active_portfolio(df_pending)

        with tab3:
            st.markdown("### 📈 Bankroll Tracker")

            STARTING_BANKROLL = current_br

            balance = [STARTING_BANKROLL]
            if not df_settled.empty:
                df_settled_sorted = df_settled.sort_values(by='kickoff')
                for _, row in df_settled_sorted.iterrows():
                    amt = row['Stake_Val']
                    if row['outcome'] == 'WON':
                        balance.append(balance[-1] + amt * (row['Dec_Odds'] - 1))
                    elif row['outcome'] == 'LOST':
                        balance.append(balance[-1] - amt)

            active_exposure = 0.0
            if not df_pending.empty:
                active_exposure = df_pending[df_pending['user_bet'] == True]['Stake_Val'].sum()

            current_balance = balance[-1] - active_exposure
            balance.append(current_balance)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Current Bankroll",
                    f"${current_balance:.2f}",
                    delta=f"${current_balance - STARTING_BANKROLL:+.2f}"
                )
            with col2:
                roi = ((current_balance - STARTING_BANKROLL) / STARTING_BANKROLL * 100) if STARTING_BANKROLL > 0 else 0
                st.metric("ROI", f"{roi:.1f}%")
            with col3:
                st.metric("Active Exposure", f"${active_exposure:.2f}")

            st.line_chart(pd.DataFrame({'Bankroll': balance}), use_container_width=True, height=300)

            st.markdown("---")
            st.markdown("### 📊 Performance by Sport")

            if not df_settled.empty:
                sports = df_settled['Sport'].unique()
                stats_data = []

                total_w, total_l, total_p = 0, 0, 0
                total_profit = 0.0
                total_stake = 0.0

                for sport in sports:
                    sdf = df_settled[df_settled['Sport'] == sport]
                    wins = len(sdf[sdf['outcome'] == 'WON'])
                    losses = len(sdf[sdf['outcome'] == 'LOST'])
                    pushes = len(sdf[sdf['outcome'] == 'PUSH'])

                    profit = 0.0
                    sport_stake = 0.0
                    for _, row in sdf.iterrows():
                        if row['outcome'] == 'WON':
                            profit += row['Stake_Val'] * (row['Dec_Odds'] - 1)
                            sport_stake += row['Stake_Val']
                        elif row['outcome'] == 'LOST':
                            profit -= row['Stake_Val']
                            sport_stake += row['Stake_Val']
                        elif row['outcome'] == 'PUSH':
                            sport_stake += row['Stake_Val']

                    roi = (profit / sport_stake * 100) if sport_stake > 0 else 0.0
                    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0

                    stats_data.append({
                        "Sport": sport,
                        "Record": f"{wins}-{losses}-{pushes}",
                        "Win %": f"{win_rate:.1f}%",
                        "Profit": f"${profit:.2f}",
                        "ROI": f"{roi:.1f}%",
                        "raw_profit": profit
                    })

                    total_w += wins
                    total_l += losses
                    total_p += pushes
                    total_profit += profit
                    total_stake += sport_stake

                perf_df = pd.DataFrame(stats_data).sort_values(by='raw_profit', ascending=False)

                tot_roi = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
                tot_win_rate = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0.0

                total_row = pd.DataFrame([{
                    "Sport": "🔥 TOTAL",
                    "Record": f"{total_w}-{total_l}-{total_p}",
                    "Win %": f"{tot_win_rate:.1f}%",
                    "Profit": f"${total_profit:.2f}",
                    "ROI": f"{tot_roi:.1f}%",
                    "raw_profit": 9999999
                }])

                final_df = pd.concat([total_row, perf_df]).drop(columns=['raw_profit'])

                st.dataframe(final_df, use_container_width=True, hide_index=True, height=400)
            else:
                st.info("📊 No settled bets to analyze yet")

            st.markdown("---")
            st.markdown("### 💰 Performance by Edge")

            if not df_settled.empty:
                # Calculate edge analysis using the backtesting module
                edge_results = analyze_by_edge_bucket(df_settled)

                if edge_results:
                    edge_df = pd.DataFrame(edge_results)
                    edge_df = edge_df.rename(columns={
                        'edge_bucket': 'Edge Range',
                        'count': 'Bets',
                        'win_rate': 'Win %',
                        'profit': 'Profit',
                        'roi': 'ROI',
                        'avg_edge': 'Avg Edge'
                    })

                    # Format display columns
                    edge_display = edge_df.copy()
                    edge_display['Win %'] = edge_display['Win %'].apply(lambda x: f"{x:.1f}%")
                    edge_display['Profit'] = edge_display['Profit'].apply(lambda x: f"${x:.2f}")
                    edge_display['ROI'] = edge_display['ROI'].apply(lambda x: f"{x:.1f}%")
                    edge_display['Avg Edge'] = edge_display['Avg Edge'].apply(lambda x: f"{x:.2f}%")

                    st.dataframe(edge_display, use_container_width=True, hide_index=True, height=300)

                    st.caption("💡 This shows how your bets perform based on the calculated edge. Higher edge bets should ideally show better ROI.")
                else:
                    st.info("📊 Not enough data for edge analysis")
            else:
                st.info("📊 No settled bets to analyze yet")

        with tab4:
            st.markdown("### 📋 Export to Spreadsheet")
            if not df_pending.empty:
                paste_df = df_pending.sort_values(by='Edge_Val', ascending=False).copy()
                cols = ['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Dec_Odds', 'Edge', 'Stake']
                st.text_area(
                    "Tab-separated data (copy & paste into Excel/Sheets):",
                    paste_df[cols].to_csv(sep='\t', index=False),
                    height=400
                )
            else:
                st.info("📭 No data to export")

    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        import traceback
        st.code(traceback.format_exc())
else:
    st.error("❌ Unable to connect to database")
