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
def fetch_live_scores(sport_keys):
    scores = {}
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key: return {}
    
    unique_sports = set(sport_keys)
    for sport in unique_sports:
        try:
            # The Odds API: Fetch scores for the sport
            url = f"https://api.the-odds-api.com/v4/sports/{sport}/scores/?apiKey={api_key}&daysFrom=3"
            res = requests.get(url, timeout=5).json()
            if isinstance(res, list):
                for game in res:
                    if game.get('completed') or game.get('scores'):
                         h = game['home_team']
                         a = game['away_team']
                         # Find scores
                         h_score = next((s['score'] for s in game['scores'] if s['name'] == h), 0)
                         a_score = next((s['score'] for s in game['scores'] if s['name'] == a), 0)
                         status = "🏁" if game['completed'] else "🔴"
                         score_str = f"{status} {h} {h_score} - {a} {a_score}"
                         scores[h] = score_str
                         scores[a] = score_str
        except: pass
    return scores

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

            if mobile_view:
                st.success("📱 Mobile View Active")
                st.subheader("🎯 Top Picks")
                if not df_pending.empty:
                    top_15 = df_pending.sort_values(by='Edge_Val', ascending=False).head(5) # Show fewer on mobile top list
                    for _, row in top_15.iterrows():
                        st.info(f"**{row['Event']}**\n\n👉 {row['Selection']} ({row['Edge']})")
            else:
                st.subheader("🎯 [TOP 15 PICKS]")
                if not df_pending.empty:
                    top_15 = df_pending.sort_values(by='Edge_Val', ascending=False).head(15)
                    st.table(top_15[['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Edge', 'Stake']])
            
            st.divider()
            now_est = pd.Timestamp.now(tz='US/Eastern')
            sniper_df = df_pending[(df_pending['user_bet'] == False) & (df_pending['kickoff'] > now_est)].copy()
            
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
                live_data = fetch_live_scores(sport_keys)
                
                # DEBUG: Show what we found
                with st.expander("Debug Live Scores", expanded=False):
                    st.write("Sports:", sport_keys)
                    st.write("Live Data Keys:", list(live_data.keys()))
                    st.write("First 5 Live Data Items:", dict(list(live_data.items())[:5]))

                def get_score(row):
                    # Match score by looking up team names
                    event = row['Event'].replace(' @ ', ' vs ')
                    teams = event.split(' vs ')
                    if len(teams) >= 2:
                        # Try exact match first
                        score = live_data.get(teams[0]) or live_data.get(teams[1])
                        if score: return score
                        
                        # Try partial match (e.g. "Buffalo" in "Buffalo Sabres")
                        for team_name in teams:
                            for live_team, live_score in live_data.items():
                                if team_name in live_team or live_team in team_name:
                                    return live_score
                                    
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

        with tab4:
            st.subheader("📋 Tabbed for Paste")
            if not df_pending.empty:
                paste_df = df_pending.sort_values(by='Edge_Val', ascending=False).copy()
                cols = ['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'Dec_Odds', 'Edge', 'Stake']
                st.text_area("Copy into Spreadsheet:", paste_df[cols].to_csv(sep='\t', index=False), height=400)

    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
