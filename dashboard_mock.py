
import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import pytz

# 🎨 Modern Page Configuration
st.set_page_config(
    page_title="Philly P Sniper (MOCK)",
    layout="wide",
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# 🎨 Custom CSS for Modern Look - DARK MODE V5
st.markdown("""
<style>
    /* Main background - Deep Navy */
    .stApp {
        background-color: #0B1120;
    }
    .main {
        background-color: #0B1120;
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

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1E293B;
        border: 1px solid #334155;
    }

    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
    }

    .stTabs [aria-selected="true"] {
        background-color: #F59E0B !important;
        color: #000000 !important;
        font-weight: bold;
    }

    /* Dataframes */
    [data-testid="stDataFrame"] {
        background-color: #1E293B;
        border: 1px solid #334155;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0F172A; /* Slate 900 */
        border-right: 1px solid #334155;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #F59E0B !important;
        border-bottom: none;
    }
    
    /* Inputs */
    .stNumberInput > div > div > input,
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        background-color: #334155 !important;
        color: #F8FAFC !important;
        border: 1px solid #475569;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #1E293B !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155;
    }
    
    /* Dividers */
    hr {
        border-color: #334155;
    }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def get_sharp_badge(row):
    """Returns modern badge HTML for sharp score"""
    raw_score = row.get("sharp_score")
    m, t = row.get("money_pct"), row.get("ticket_pct")

    if pd.isna(raw_score) or raw_score is None:
        return '<span style="background: #334155; color: #94A3B8; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">⚪ NO DATA</span>'

    try:
        score = float(raw_score)
        
        # Public heavy? (Money <= Tickets)
        if pd.notnull(m) and pd.notnull(t):
             if float(m) <= float(t): # More tickets than money
                  return f'<span style="background: #334155; color: #94A3B8; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">🤡 PUBLIC ({int(round(score))})</span>'
                  
        # Format Splits if available
        split_info = ""
        if pd.notnull(m) and pd.notnull(t):
            split_info = f" <span style='font-size: 10px; opacity: 0.8;'>({int(m)}%💰 {int(t)}%🎟️)</span>"

        s = int(round(score))
        if s >= 75:
            return f'<span style="background: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 1px solid #F59E0B; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">🔥 SHARP ({s}){split_info}</span>'
        if s >= 50:
            return f'<span style="background: rgba(59, 130, 246, 0.2); color: #60A5FA; border: 1px solid #60A5FA; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">🧠 SHARP ({s}){split_info}</span>'
        if s >= 25:
             return f'<span style="background: rgba(226, 232, 240, 0.1); color: #E2E8F0; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">🧠 LEAN ({s}){split_info}</span>'
             
        return f'<span style="background: #334155; color: #94A3B8; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">⚪ NO SIGNAL ({s}){split_info}</span>'
    except:
        return '<span style="background: #991B1B; color: #FCA5A5; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">⚠️ ERROR</span>'

def get_last_update_time():
    return "Jan 23, 09:15 PM EST (MOCK)"

# Mock Data Generation
def get_mock_data():
    now = datetime.now(pytz.utc)
    future = now + timedelta(hours=2)
    
    data = []
    
    # 1. Top 15 Scenario (High Edge)
    for i in range(5):
        data.append({
            'event_id': f'evt_{i}',
            'timestamp': now,
            'kickoff': future + timedelta(hours=i),
            'sport': 'basketball_nba' if i % 2 == 0 else 'icehockey_nhl',
            'teams': f'Team {i}A vs Team {i}B',
            'selection': f'Team {i}A -5',
            'odds': 1.91,
            'edge': 0.05 + (i * 0.01), # 5% to 10% edge
            'stake': 100.0,
            'user_bet': False,
            'user_odds': None,
            'user_stake': None,
            'outcome': 'PENDING',
            'sharp_score': 60,
            'money_pct': 55,
            'ticket_pct': 45
        })
        
    # 2. Sharp Intel Scenario (High Sharp Score, Money > Tickets)
    for i in range(5, 8):
        data.append({
            'event_id': f'evt_{i}',
            'timestamp': now,
            'kickoff': future + timedelta(hours=i),
            'sport': 'americanfootball_nfl',
            'teams': f'Sharp Team {i} vs Public Team {i}',
            'selection': f'Sharp Team {i} +3',
            'odds': 2.0,
            'edge': 0.01, # Low edge, wouldn't show in Top 15
            'stake': 50.0,
            'user_bet': False,
            'user_odds': None,
            'user_stake': None,
            'outcome': 'PENDING',
            'sharp_score': 85,
            'money_pct': 80,
            'ticket_pct': 40
        })

    df = pd.DataFrame(data)
    return df

# Header
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    st.markdown("<h1 style='text-align: center; color: #F59E0B;'>🎯 PHILLY EDGE: AI (MOCK)</h1>", unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    last_run = get_last_update_time()
    st.caption(f"Last Updated: {last_run}")
    st.divider()

# Main Logic MOCK
df_p = get_mock_data()
df_s = pd.DataFrame()

def clean_df(df):
    if df.empty: return df
    # Mock timezone conversion if needed, or just ensure datetime
    if not isinstance(df['kickoff'].dtype, pd.DatetimeTZDtype):
        df['kickoff'] = pd.to_datetime(df['kickoff'])
        if df['kickoff'].dt.tz is None:
            df['kickoff'] = df['kickoff'].dt.tz_localize('UTC')
        df['kickoff'] = df['kickoff'].dt.tz_convert('US/Eastern')
            
    df['Date'] = df['kickoff'].dt.strftime('%Y-%m-%d')
    df['Kickoff'] = df['kickoff'].dt.strftime('%m-%d %H:%M')
    df['Sport'] = df['sport'].apply(lambda x: x.split('_')[-1].upper() if '_' in x else x)
    df['Event'] = df['teams']
    df['Selection'] = df['selection']

    df['Stake_Val'] = df['stake'].astype(float)
    df['Stake'] = df['Stake_Val'].apply(lambda x: f"${x:.2f}")
    df['Dec_Odds'] = df['odds'].astype(float)
    df['Edge_Val'] = pd.to_numeric(df['edge'], errors='coerce').fillna(0)
    df['Edge'] = df['Edge_Val'].apply(lambda x: f"{x*100:.1f}%")
    return df

df_pending = clean_df(df_p)

# Tab Structure
tab1, tab2, tab3, tab4, tab5 = st.tabs(["⚡ Live Edge Feed", "💼 Active Portfolio", "📈 Performance Analytics", "⚽ Player Props", "🛠️ Admin Tools"])

# --- TAB 1: LIVE FEED ---
# --- TIMESTAMP & HEADER (VERIFICATION TARGET) ---
st.markdown("---")
last_run = get_last_update_time()
st.markdown(f"<h4 style='text-align: center; color: #94A3B8; margin-bottom: 20px;'>🕒 Last Updated: <span style='color: #F59E0B;'>{last_run}</span></h4>", unsafe_allow_html=True)

with tab1:
    if not df_pending.empty:
        now_est = pd.Timestamp.now(tz='US/Eastern')
        
        # --- SECTION 1: TOP 15 OPPORTUNITIES (3-15% Edge) (VERIFICATION TARGET) ---
        st.markdown("### ⚡ Top 15 Opportunities (3-15% Edge)")
        st.caption("Best value plays from every available sport, sorted by kickoff.")
        
        top_pool = df_pending[
            (df_pending['user_bet'] == False) & 
            (df_pending['kickoff'] > now_est) &
            (df_pending['Edge_Val'] >= 0.03) & 
            (df_pending['Edge_Val'] <= 0.15)
        ].copy()
        
        # ... logic from dashboard.py ...
        top_picks = []
        if not top_pool.empty:
            sports = top_pool['Sport'].unique()
            used_indices = set()
            for sport in sports:
                sport_df = top_pool[top_pool['Sport'] == sport].sort_values('Edge_Val', ascending=False)
                if not sport_df.empty:
                    best_row = sport_df.iloc[0]
                    top_picks.append(best_row)
                    used_indices.add(best_row.name)
            remaining_slots = 15 - len(top_picks)
            if remaining_slots > 0:
                rest_df = top_pool[~top_pool.index.isin(used_indices)]
                rest_df = rest_df.sort_values('kickoff', ascending=True)
                top_picks.extend([r for _, r in rest_df.head(remaining_slots).iterrows()])
            final_top_df = pd.DataFrame(top_picks).sort_values('kickoff', ascending=True)
            
            t_cols = st.columns(3)
            for idx, (_, row) in enumerate(final_top_df.iterrows()):
                badge = get_sharp_badge(row)
                with t_cols[idx % 3]:
                    st.markdown(f"""
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
                    """, unsafe_allow_html=True)
        else:
            st.info("No plays found fitting the Top 15 criteria.")

        st.divider()

        # --- SECTION 2: SHARP INTEL (VERIFICATION TARGET) ---
        st.markdown("### 🧠 Sharp Intel")
        st.info("ℹ️ **Explainer**: These plays feature high Sharp Scores (>= 70), indicating significant 'Smart Money' action (High Money % vs Low Ticket %). They may not fit our statistical model's edge criteria, but the market is moving heavily on them.")
        
        sharp_pool = df_pending[
            (df_pending['user_bet'] == False) & 
            (df_pending['kickoff'] > now_est) &
            (pd.to_numeric(df_pending['sharp_score'], errors='coerce') >= 70)
        ].copy()
        
        if not sharp_pool.empty:
            sharp_pool = sharp_pool.sort_values('kickoff', ascending=True)
            s_cols = st.columns(3)
            for idx, (_, row) in enumerate(sharp_pool.iterrows()):
                 badge = get_sharp_badge(row)
                 with s_cols[idx % 3]:
                    st.markdown(f"""
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
                    """, unsafe_allow_html=True)
