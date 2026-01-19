import streamlit as st
import pandas as pd
import psycopg2
import os
import requests
from datetime import datetime

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
    /* Main background and text */
    .main {
        background-color: #0e1117;
    }

    /* Headers */
    h1 {
        color: #ffffff;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        color: #fafafa;
        font-weight: 600;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: 700;
    }

    /* Cards with borders */
    [data-testid="stHorizontalBlock"] {
        background-color: #1a1d24;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2d3139;
        margin-bottom: 15px;
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
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1a1d24;
        padding: 8px;
        border-radius: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #262a33;
        border-radius: 8px;
        color: #9ca3af;
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
        background-color: #1a1d24;
        border-radius: 10px;
        border: 1px solid #2d3139;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1d24;
    }

    /* Dividers */
    hr {
        margin: 30px 0;
        border-color: #2d3139;
    }

    /* Containers */
    .element-container {
        margin-bottom: 10px;
    }

    /* Captions */
    .st-emotion-cache-16idsys p {
        color: #9ca3af;
        font-size: 14px;
    }

    /* Success/Info/Warning boxes */
    .stSuccess {
        background-color: #1a3d2e;
        border-left: 4px solid #10b981;
        border-radius: 8px;
    }

    .stInfo {
        background-color: #1e3a5f;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
    }

    .stWarning {
        background-color: #3d2a1a;
        border-left: 4px solid #f59e0b;
        border-radius: 8px;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #262a33;
        border-radius: 8px;
        font-weight: 600;
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
    games = []
    logs = []
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        return [], ["❌ No API Key"]

    unique_sports = set(sport_keys)
    SPORT_MAP = {
        'NBA': 'basketball_nba',
        'NCAAB': 'basketball_ncaab',
        'NFL': 'americanfootball_nfl',
        'NHL': 'icehockey_nhl',
        'MLB': 'baseball_mlb',
        'SOCCER': 'soccer_epl'
    }

    for sport_short in unique_sports:
        try:
            sport = SPORT_MAP.get(sport_short, sport_short)
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/scores/?apiKey={api_key}&daysFrom=3"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                res = r.json()
                for g in res:
                    if g.get('scores'):
                        h = g['home_team']
                        a = g['away_team']
                        h_s = next((s['score'] for s in g['scores'] if s['name'] == h), 0)
                        a_s = next((s['score'] for s in g['scores'] if s['name'] == a), 0)
                        status = "🏁" if g['completed'] else "🔴 LIVE"
                        games.append({
                            'home': h,
                            'away': a,
                            'score': f"{status} {h} {h_s} - {a} {a_s}",
                            'commence': g['commence_time']
                        })
            else:
                logs.append(f"⚠️ {sport}: {r.status_code}")
        except Exception as e:
            logs.append(f"❌ {sport}: {e}")

    return games, logs

# --- Header ---
col1, col2, col3 = st.columns([2, 3, 2])
with col2:
    st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🎯 Philly P Sniper</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 16px; margin-top: 0;'>Advanced Betting Intelligence Platform</p>", unsafe_allow_html=True)

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
            df['Kickoff'] = df['kickoff'].dt.strftime('%H:%M')
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

        tab1, tab2, tab3, tab4 = st.tabs(["🔫 Live Sniper Feed", "💼 Active Portfolio", "📈 Performance Analytics", "📋 Export Data"])

        with tab1:
            if not df_pending.empty:
                st.markdown("### 🎯 Top Opportunities")
                top_15 = df_pending.sort_values(by='Edge_Val', ascending=False).head(15)

                if mobile_view:
                    for _, row in top_15.iterrows():
                        with st.container():
                            st.markdown(f"""
                            <div style='background: linear-gradient(135deg, #1a1d24 0%, #262a33 100%); padding: 15px; border-radius: 10px; border-left: 4px solid #667eea; margin-bottom: 10px;'>
                                <p style='color: #9ca3af; font-size: 12px; margin: 0;'>{row['Sport']} • {row['Kickoff']}</p>
                                <p style='color: white; font-size: 16px; font-weight: 600; margin: 5px 0;'>{row['Event']}</p>
                                <p style='color: #667eea; font-size: 14px; margin: 5px 0;'>👉 {row['Selection']} @ {row['Dec_Odds']:.2f}</p>
                                <p style='color: #10b981; font-size: 14px; margin: 5px 0;'>Edge: {row['Edge']} | Stake: {row['Stake']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    display_cols = ['Sport', 'Kickoff', 'Event', 'Selection', 'Dec_Odds', 'Edge', 'Stake']
                    st.dataframe(top_15[display_cols], use_container_width=True, hide_index=True, height=400)
            else:
                st.info("📭 No opportunities available at the moment")

            st.markdown("---")
            st.markdown("### 🎰 All Available Plays")

            now_est = pd.Timestamp.now(tz='US/Eastern')
            sniper_df = df_pending[(df_pending['user_bet'] == False) & (df_pending['kickoff'] > now_est)].copy()

            if 'sharp_score' in sniper_df.columns:
                sniper_df = sniper_df[pd.to_numeric(sniper_df['sharp_score'], errors='coerce').fillna(0) >= sharp_filter]

            if sniper_df.empty:
                st.info("🎯 No plays match your current filters")
            else:
                for index, row in sniper_df.iterrows():
                    badge = get_sharp_badge(row)

                    with st.container():
                        if mobile_view:
                            st.markdown(f"""
                            <div style='background: #1a1d24; padding: 20px; border-radius: 10px; border: 1px solid #2d3139; margin-bottom: 15px;'>
                                <p style='color: #9ca3af; font-size: 13px; margin-bottom: 8px;'>{row['Sport']} • Kickoff: {row['Kickoff']}</p>
                                <h4 style='color: white; margin: 8px 0;'>{row['Event']}</h4>
                                <p style='color: #667eea; font-size: 16px; font-weight: 600; margin: 10px 0;'>👉 {row['Selection']} @ {row['Dec_Odds']:.2f}</p>
                                <div style='margin: 15px 0;'>
                                    <span style='color: #10b981; font-size: 14px; margin-right: 20px;'>Edge: {row['Edge']}</span>
                                    <span style='color: #f59e0b; font-size: 14px;'>Stake: {row['Stake']}</span>
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
            st.markdown("### 💼 Your Active Wagers")
            my_bets = df_pending[df_pending['user_bet'] == True].copy()

            if my_bets.empty:
                st.info("📭 No active bets in your portfolio")
            else:
                sport_keys = my_bets['sport'].unique()
                live_games, debug_logs = fetch_live_games(sport_keys)

                with st.expander("🔍 Live Score Debug", expanded=False):
                    for l in debug_logs:
                        st.text(l)
                    st.write(f"Found {len(live_games)} live games")

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

                    return "🕒 Upcoming"

                my_bets['Live Score'] = my_bets.apply(get_score, axis=1)

                st.dataframe(
                    my_bets[['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Live Score', 'Dec_Odds', 'Stake']],
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )

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
