import streamlit as st
import pandas as pd
import psycopg2
import os
import requests
from datetime import datetime

# 🎯 STEP 1: Page Configuration
st.set_page_config(page_title="Philly P Sniper", layout="wide", page_icon="🎯")

# --- 1. Database Connection Setup ---
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

# --- 2. Security & Cleanup Logic ---
def surgical_cleanup():
    conn = get_db()
    if conn:
        try:
            cur = conn.cursor()
            # Deletes only untracked pending bets
            cur.execute("DELETE FROM intelligence_log WHERE outcome = 'PENDING' AND user_bet = FALSE;")
            conn.commit()
            st.sidebar.success(f"🧹 Cleaned {cur.rowcount} ghost bets!")
            cur.close()
            conn.close()
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Cleanup failed: {e}")


# --- 3. UI Helpers ---
def get_sharp_style(row):
    raw_score = row.get("sharp_score")
    m, t = row.get("money_pct"), row.get("ticket_pct")
    if pd.isna(raw_score) or raw_score is None:
        return "⚪ NO DATA", "#808080"
    try:
        score = float(raw_score)
        if pd.notnull(m) and pd.notnull(t):
            if float(m) <= float(t):
                return f"🤡 PUBLIC ({int(round(score))})", "#808080"
        s = int(round(score))
        if s >= 75: return f"🔥 SHARP ({s})", "#2ecc71"
        if s >= 50: return f"🧠 SHARP ({s})", "#27ae60"
        if s >= 25: return f"🧠 LEAN ({s})", "#f39c12"
        return f"⚪ NO SIGNAL ({s})", "#808080"
    except: return "⚪ ERROR", "#808080"

def get_starting_bankroll():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT value FROM app_settings WHERE key='starting_bankroll'")
        row = cur.fetchone()
        return float(row[0]) if row else 451.16
    except: return 451.16

def update_bankroll(val):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO app_settings (key, value) VALUES ('starting_bankroll', %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (str(val),))
        conn.commit()
        st.rerun()
    except Exception as e: st.error(f"Failed to update: {e}")

def confirm_bet(event_id, current_status, user_odds=None, user_stake=None):
    conn = get_db()
    try:
        cur = conn.cursor()
        new_status = not current_status
        # If we are verifying a bet (turning it ON), save the user inputs
        if new_status and user_odds is not None:
             cur.execute("""
                UPDATE intelligence_log 
                SET user_bet = %s, user_odds = %s, user_stake = %s 
                WHERE event_id = %s
             """, (new_status, float(user_odds), float(user_stake), event_id))
        else:
            # If turning OFF, just toggle status (keep inputs or clear them? Keeping them is safer for history)
            # Actually if turning OFF we might want to keep the record but just mark as not active.
            # But the user might just be toggling off. Let's just toggle status.
            cur.execute("UPDATE intelligence_log SET user_bet = %s WHERE event_id = %s", (new_status, event_id))
            
        conn.commit(); cur.close(); st.rerun()
    except Exception as e: st.error(f"Error: {e}")


    
@st.cache_data(ttl=60)
def fetch_live_games(sport_keys):
    games = []
    logs = []
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key: return [], ["❌ No API Key"]
    
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
                    if g.get('scores'): # Only care if scores exist
                        h = g['home_team']
                        a = g['away_team']
                        h_s = next((s['score'] for s in g['scores'] if s['name'] == h), 0)
                        a_s = next((s['score'] for s in g['scores'] if s['name'] == a), 0)
                        status = "🏁" if g['completed'] else "🔴"
                        games.append({
                            'home': h, 'away': a,
                            'score': f"{status} {h} {h_s} - {a} {a_s}",
                            'commence': g['commence_time']
                        })
            else:
                logs.append(f"⚠️ {sport}: {r.status_code}")
        except Exception as e:
            logs.append(f"❌ {sport}: {e}")
            
    return games, logs

# --- 4. Main Dashboard ---
st.title("🎯 Philly P Sniper: Live Dashboard")

with st.sidebar:
    # 🔒 PASSWORD PROTECTION FOR CLEANUP & SETTINGS
    with st.expander("🛠️ Admin Controls"):
        pw_input = st.text_input("Admin Key", type="password", help="Enter key to enable checks")
        correct_pw = os.getenv("DASHBOARD_PASSWORD", "default_secret")
        
        st.caption("Maintenance")
        if st.button("🧹 Clear Ghost Bets", use_container_width=True):
            if pw_input == correct_pw:
                surgical_cleanup()
            else:
                st.error("Invalid Admin Key")
        
        st.divider()
        st.caption("Bankroll Settings")
        current_br = get_starting_bankroll()
        new_br = st.number_input("Starting Bankroll ($)", value=current_br, step=10.0)
        if new_br != current_br:
            if st.button("💾 Save Bankroll"):
                if pw_input == correct_pw:
                    update_bankroll(new_br)
                else:
                    st.error("Invalid Admin Key")
    
    st.divider()
    sharp_filter = st.slider("Min Sharp Score", 0, 100, 0)
    mobile_view = st.checkbox("📱 Mobile View", value=False)
    if st.button("🔄 Refresh Data", use_container_width=True): st.rerun()

conn = get_db()
if conn:
    try:
        # DATA STREAM 1: Pending (Filter stale bets older than 24h)
        df_p = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome = 'PENDING' AND timestamp >= NOW() - INTERVAL '24 HOURS' ORDER BY kickoff ASC LIMIT 500", conn)
        df_s = pd.read_sql("SELECT * FROM intelligence_log WHERE outcome IN ('WON', 'LOST', 'PUSH') ORDER BY kickoff DESC", conn)
        conn.commit() # Close transaction to release locks
        
        def clean_df(df):
            if df.empty: return df
            df['kickoff'] = pd.to_datetime(df['kickoff']).dt.tz_localize('UTC', ambiguous='infer').dt.tz_convert('US/Eastern')
            df['Date'] = df['kickoff'].dt.strftime('%Y-%m-%d')
            df['Kickoff'] = df['kickoff'].dt.strftime('%H:%M')
            df['Sport'] = df['sport'].apply(lambda x: x.split('_')[-1].upper() if '_' in x else x)
            df['Event'] = df['teams']
            df['Selection'] = df['selection']
            
            # Use user_stake/user_odds if available (for portfolio calculations)
            # Note: df might not have user_odds column yet if DB wasn't fully migrated when reading. 
            # safe get of columns
            
            def get_val(row, col_base):
                user_col = f"user_{col_base}"
                if user_col in row and pd.notnull(row[user_col]):
                    return float(row[user_col])
                return float(row[col_base]) if pd.notnull(row[col_base]) else 0.0

            df['Stake_Val'] = df.apply(lambda row: get_val(row, 'stake'), axis=1)
            df['Stake_Val'] = df['Stake_Val'].apply(lambda x: max(1.00, x))
            df['Stake'] = df['Stake_Val'].apply(lambda x: f"${x:.2f}")
            
            df['Dec_Odds'] = df.apply(lambda row: get_val(row, 'odds'), axis=1) # Default to odds if user_odds missing
            
            df['Edge_Val'] = pd.to_numeric(df['edge'], errors='coerce').fillna(0)
            df['Edge'] = df['Edge_Val'].apply(lambda x: f"{x*100:.1f}%")
            return df

        df_pending = clean_df(df_p)
        df_settled = clean_df(df_s)

        tab1, tab2, tab3, tab4 = st.tabs(["🔫 Live Sniper", "💼 Portfolio", "📊 Performance", "📋 Paste"])

        with tab1:
            
            # Global filter for Tab 1: Only show future games
            now_est = pd.Timestamp.now(tz='US/Eastern')
            future_pending = df_pending[df_pending['kickoff'] > now_est]

            if mobile_view:
                st.success("📱 Mobile View Active")
                st.subheader("🎯 Top Picks")
                if not future_pending.empty:
                    top_15 = future_pending.sort_values(by='Edge_Val', ascending=False).head(5) # Show fewer on mobile top list
                    for _, row in top_15.iterrows():
                        st.info(f"**{row['Event']}**\n\n👉 {row['Selection']} ({row['Edge']})")
            else:
                st.subheader("🎯 [TOP 15 PICKS]")
                if not future_pending.empty:
                    top_15 = future_pending.sort_values(by='Edge_Val', ascending=False).head(15)
                    st.table(top_15[['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Edge', 'Stake']])
            
            st.divider()
            sniper_df = future_pending[future_pending['user_bet'] == False].copy()
            
            if 'sharp_score' in sniper_df.columns:
                sniper_df = sniper_df[pd.to_numeric(sniper_df['sharp_score'], errors='coerce').fillna(0) >= sharp_filter]
            
            for index, row in sniper_df.iterrows():
                label, color = get_sharp_style(row)
                
                if mobile_view:
                     with st.container(border=True):
                        st.caption(f"{row['Sport']} • {row['Kickoff']}")
                        st.markdown(f"**{row['Event']}**")
                        st.markdown(f"👉 **{row['Selection']}** @ {row['Dec_Odds']:.2f}")
                        
                        c1, c2 = st.columns(2)
                        c1.metric("Edge", row['Edge'])
                        c1.metric("Stake", row['Stake'])
                        c2.markdown(f"<span style='color:{color}; font-weight:bold;'>{label}</span>", unsafe_allow_html=True)
                        if pd.notnull(row['money_pct']): c2.caption(f"💰 {int(row['money_pct'])}% | 🎟️ {int(row['ticket_pct'])}%")
                        
                        with st.expander("✅ Track Bet", expanded=False):
                            u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), key=f"uo_{row['event_id']}")
                            u_stake = st.number_input("Stake ($)", value=float(row['Stake_Val']), key=f"us_{row['event_id']}")
                            if st.button("Confirm", key=f"btn_{row['event_id']}"):
                                confirm_bet(row['event_id'], row['user_bet'], u_odds, u_stake)

                else:
                    with st.container():
                        c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 3, 2, 1.2, 1.2, 2.5, 1.5])
                        c1.caption(f"{row['Sport']}"); c1.text(row['Kickoff'])
                        c2.markdown(f"**{row['Event']}**")
                        c3.markdown(f"👉 **{row['Selection']}**"); c3.caption(f"@{row['Dec_Odds']:.2f}")
                        c4.metric("Edge", row['Edge'])
                        c5.metric("Stake", row['Stake'])
                        c6.markdown(f"<span style='color:{color}; font-weight:bold;'>{label}</span>", unsafe_allow_html=True)
                        if pd.notnull(row['money_pct']): c6.caption(f"💰 {int(row['money_pct'])}% | 🎟️ {int(row['ticket_pct'])}%")
                        
                        # Custom input popover logic for desktop too? The user asked for it in general.
                        # Using expander inside column might be tight.
                        # Let's use an expander in the last column or just replace the button with an expander.
                        with c7:
                            with st.expander("Track"):
                                u_odds = st.number_input("Odds", value=float(row['Dec_Odds']), label_visibility="collapsed", key=f"d_uo_{row['event_id']}")
                                u_stake = st.number_input("Stake", value=float(row['Stake_Val']), label_visibility="collapsed", key=f"d_us_{row['event_id']}")
                                if st.button("✅", key=f"d_btn_{row['event_id']}"):
                                    confirm_bet(row['event_id'], row['user_bet'], u_odds, u_stake)
                        st.divider()

        with tab2:
            st.subheader("💼 Active Wagers")
            my_bets = df_pending[df_pending['user_bet'] == True].copy()
            if my_bets.empty: 
                st.info("No active bets.")
            else: 
                # Live Score Integration
                sport_keys = my_bets['sport'].unique()
                live_games, debug_logs = fetch_live_games(sport_keys)
                
                # DEBUG: Show what we found
                with st.expander("Debug Live Scores", expanded=False):
                    for l in debug_logs: st.text(l)
                    st.write(f"Found {len(live_games)} live games")

                def get_score(row):
                    event = row['Event'].replace(' @ ', ' vs ')
                    teams = event.split(' vs ')
                    if len(teams) < 2: return "Upcoming 🕒"
                    
                    t1, t2 = teams[0], teams[1]
                    
                    for g in live_games:
                        # Check strictly if BOTH teams are in the game object
                        # We use simple string inclusion because "Buffalo" is in "Buffalo Sabres"
                        # But we demand BOTH match to avoid "Washington Capitals" matching "Washington Wizards" vs "Miami Heat" (unlikely across sports but still)
                        
                        h, a = g['home'], g['away']
                        
                        # Match t1 against home OR away
                        t1_match = (t1 in h or h in t1) or (t1 in a or a in t1)
                        # Match t2 against home OR away
                        t2_match = (t2 in h or h in t2) or (t2 in a or a in t2)
                        
                        if t1_match and t2_match:
                            return g['score']
                            
                    return "Upcoming 🕒"

                my_bets['Live Score'] = my_bets.apply(get_score, axis=1)
                st.dataframe(my_bets[['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Live Score', 'Dec_Odds', 'Stake']], use_container_width=True)

        with tab3:
            st.subheader("📈 Bankroll Performance")
            
            # --- FETCH DYNAMIC BANKROLL --- 
            # We already defined get_starting_bankroll in sidebar scope, but need to call it or redefine/reuse if scopes are tricky in Streamlit.
            # Simpler to just query again or move function to top. 
            # Since user might have just updated it, querying is fine.
            # Actually, let's just use the `current_br` variable from sidebar if available? 
            # Streamlit reruns the whole script top to bottom. `current_br` is available.
            
            STARTING_BANKROLL = current_br     
            
            # Calculate settled balance
            balance = [STARTING_BANKROLL]
            if not df_settled.empty:
                df_settled = df_settled.sort_values(by='kickoff')
                for _, row in df_settled.iterrows():
                    amt = row['Stake_Val']
                    if row['outcome'] == 'WON': balance.append(balance[-1] + amt * (row['Dec_Odds'] - 1))
                    elif row['outcome'] == 'LOST': balance.append(balance[-1] - amt)
            
            # Calculate active exposure (pending bets)
            active_exposure = 0.0
            if not df_pending.empty:
                active_exposure = df_pending[df_pending['user_bet'] == True]['Stake_Val'].sum()
            
            current_balance = balance[-1] - active_exposure
            
            # Update chart data to reflect current state
            # append the "live" balance as the latest point so the chart drops immediately
            balance.append(current_balance) 

            st.metric("Bankroll", f"${current_balance:.2f}", delta=f"{current_balance - STARTING_BANKROLL:+.2f}")
            st.caption(f"Active Exposure: ${active_exposure:.2f}")
            st.line_chart(pd.DataFrame({'Bankroll': balance}))

            st.divider()
            st.subheader("📊 Model Performance by Sport")
            
            if not df_settled.empty:
                # Group by Sport
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
                    
                    # Calculate profit
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
                            sport_stake += row['Stake_Val'] # Count stake for ROI? Usually yes or no depending on pref. Let's include denominator.
                    
                    roi = (profit / sport_stake * 100) if sport_stake > 0 else 0.0
                    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0.0
                    
                    stats_data.append({
                        "Sport": sport,
                        "Record": f"{wins}-{losses}-{pushes}",
                        "Win %": f"{win_rate:.1f}%",
                        "Profit": f"${profit:.2f}",
                        "ROI": f"{roi:.1f}%",
                        "raw_profit": profit # For sorting
                    })
                    
                    total_w += wins; total_l += losses; total_p += pushes
                    total_profit += profit; total_stake += sport_stake
                
                # Create DF
                perf_df = pd.DataFrame(stats_data).sort_values(by='raw_profit', ascending=False)
                
                # Total Row
                tot_roi = (total_profit / total_stake * 100) if total_stake > 0 else 0.0
                tot_win_rate = (total_w / (total_w + total_l) * 100) if (total_w + total_l) > 0 else 0.0
                
                # Append Total using pandas (concat)
                total_row = pd.DataFrame([{
                    "Sport": "🔥 TOTAL", 
                    "Record": f"{total_w}-{total_l}-{total_p}",
                    "Win %": f"{tot_win_rate:.1f}%",
                    "Profit": f"${total_profit:.2f}",
                    "ROI": f"{tot_roi:.1f}%",
                    "raw_profit": 9999999 # Keep at top or bottom? Let's put at top
                }])
                
                final_df = pd.concat([total_row, perf_df]).drop(columns=['raw_profit'])
                
                st.dataframe(final_df, use_container_width=True, hide_index=True)
            else:
                st.info("No settled bets to analyze yet.")

        with tab4:
            st.subheader("📋 Tabbed for Paste")
            if not df_pending.empty:
                paste_df = df_pending.sort_values(by='Edge_Val', ascending=False).copy()
                cols = ['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Dec_Odds', 'Edge', 'Stake']
                st.text_area("Copy into Spreadsheet:", paste_df[cols].to_csv(sep='\t', index=False), height=400)

    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
