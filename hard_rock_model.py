
"""
Philly P Sniper - Automated Sports Betting Intelligence System

Main orchestrator that coordinates all modules to identify profitable betting opportunities.
"""

import requests
import pandas as pd
import joblib
import os
from datetime import datetime, timedelta, timezone

from config import Config
from utils import log, match_team
from database import get_db, init_db, get_calibration
from notifier import send_alert, format_opportunity
from bet_grading import settle_pending_bets
from ratings import get_team_ratings
from api_clients import get_action_network_data, get_soccer_predictions, get_nhl_player_stats, fetch_espn_scores, get_nba_refs
from probability_models import process_markets, process_nhl_props
from closing_line import fetch_closing_odds
from smart_staking import get_performance_multipliers, print_multiplier_report

def run_sniper():
    """Main execution function that orchestrates the betting intelligence pipeline."""
    log("INIT", "Starting Philly P Sniper...")

    # Initialize database
    init_db()

    # Settle any pending bets that have completed
    settle_pending_bets()

    # --- FATIGUE / SCHEDULE TRACKING ---
    # Fetch scores from Yesterday and Day Before to calculate Rest Days
    log("FATIGUE", "Building Team Schedule History (Rest Days)...")
    history_games = []
    
    # Dates to check: Yesterday and 2 Days Ago 
    utc_now = datetime.now(timezone.utc)
    
    dates_to_fetch = [
        (utc_now - timedelta(days=1)).strftime('%Y%m%d'),
        (utc_now - timedelta(days=2)).strftime('%Y%m%d')
    ]
    
    all_sports = ['NBA', 'NCAAB', 'NHL', 'NFL'] 
    
    for d in dates_to_fetch:
        try:
            # We fetch all relevant sports for this date
            g = fetch_espn_scores(all_sports, specific_date=d)
            history_games.extend(g)
        except Exception as e:
            log("WARN", f"Failed to fetch history for {d}: {e}")

    # Build Map: standard_name -> last_game_date_obj
    last_played_map = {}
    
    for g in history_games:
        h_team = g.get('home')
        a_team = g.get('away')
        g_date = datetime.fromisoformat(g['commence'].replace('Z', '+00:00'))
        
        if h_team:
            last_played_map[h_team] = g_date
        if a_team:
            last_played_map[a_team] = g_date
            
    log("FATIGUE", f" tracked {len(last_played_map)} teams with recent games.")

    # Fetch closing odds for bets about to start (CLV tracking)
    fetch_closing_odds()

    # Get smart staking multipliers based on historical performance
    log("SMART_STAKE", "Calculating performance-based stake multipliers...")
    multipliers = get_performance_multipliers(days_back=60, min_bets=10)
    if multipliers:
        print_multiplier_report(multipliers)
    else:
        log("SMART_STAKE", "Not enough historical data yet, using standard Kelly")

    # Fetch team ratings from multiple sources
    ratings = get_team_ratings()

    # Fetch public betting splits
    sharp_data = get_action_network_data()

    # Pre-fetch NHL Player Stats
    nhl_player_stats = get_nhl_player_stats()
    print(f"📊 [DEBUG] Loaded {len(nhl_player_stats)} NHL Players")

    # --- NBA REFS ---
    nba_ref_assignments = get_nba_refs()
    
    # Build Map for Refs: TeamName -> {Chief, Ref, Umpire}
    nba_ref_map = {}
    for assignment in nba_ref_assignments:
        game_title = assignment.get('Game', '')
        if '@' in game_title:
            try:
                away_raw, home_raw = game_title.split('@')
                nba_ref_map[away_raw.strip()] = assignment
                nba_ref_map[home_raw.strip()] = assignment
            except:
                pass

    # Get database connection
    conn = get_db()
    cur = conn.cursor() if conn else None

    all_opps = []

    # Define time window for opportunities
    now_utc = datetime.now(timezone.utc)
    limit_time = now_utc + timedelta(hours=72)
    log("TIME", f"Window: {now_utc.strftime('%Y-%m-%d %H:%M')} UTC to {limit_time.strftime('%Y-%m-%d %H:%M')} UTC")

    # Process each league
    for league in Config.LEAGUES:
        sport_key = league.split('_')[-1].upper()
        target_sport = 'NBA' if 'nba' in league else 'NCAAB' if 'ncaab' in league else 'NFL' if 'nfl' in league else 'NHL'

        # Get calibration factor based on historical performance
        calibration = get_calibration(target_sport)
        log("SCAN", f"Scanning {sport_key} ({league})... Calibration: {calibration:.2f}x")

        # Get soccer predictions if applicable
        preds = get_soccer_predictions(league) if 'soccer' in league else {}

        try:
            # Fetch odds from The Odds API
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.MAIN_MARKETS}"
            r = requests.get(url, timeout=15)
            res = r.json()
            
            # TRACK USAGE
            try:
                quota_used = r.headers.get('x-requests-used', 'Unknown')
                quota_remaining = r.headers.get('x-requests-remaining', 'Unknown')
                log("API_QUOTA", f"Used: {quota_used} | Remaining: {quota_remaining}")
            except:
                pass

            if not isinstance(res, list):
                continue

            # Filter matches within time window
            matches = []
            for m in res:
                mdt = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00'))
                if mdt > limit_time:
                    continue
                matches.append(m)

            log("SCAN", f"Found {len(matches)} matches")

            # Load NHL Utils if needed
            nhl_ref_model = None
            nhl_assignments = []
            if sport_key == 'NHL':
                 from nhl_modeling import NHLRefModel
                 from nhl_assignments import get_nhl_assignments
                 nhl_ref_model = NHLRefModel()
                 nhl_assignments = get_nhl_assignments() # Fetches web data


            # Process each match
            seen_matches = set()
             
            # Pre-process NHL Assignments into a Map if loaded
            nhl_ref_map = {}
            if sport_key == 'NHL' and nhl_assignments:
                for assignment in nhl_assignments:
                    game_title = assignment.get('Game', '')
                    # Expected: "Away at Home"
                    if ' at ' in game_title:
                        parts = game_title.split(' at ')
                        if len(parts) == 2:
                            a_raw = parts[0].strip()
                            h_raw = parts[1].strip()
                            nhl_ref_map[a_raw] = assignment
                            nhl_ref_map[h_raw] = assignment
                             
            for m in matches:
                # --- NHL REFS ---
                ref_impact = 0.0
                if sport_key == 'NHL' and nhl_ref_model and nhl_ref_map:
                     h_team = m.get('home_team')
                     a_team = m.get('away_team')
                     
                     matched_refs = []
                     
                     # Try to find team in our map using fuzzy match
                     # 1. Direct lookup
                     # 2. match_team lookup
                     
                     found_assign = None
                     
                     # Try Home
                     if h_team in nhl_ref_map:
                         found_assign = nhl_ref_map[h_team]
                     else:
                         # Fuzzy
                         match_h = match_team(h_team, nhl_ref_map.keys())
                         if match_h:
                             found_assign = nhl_ref_map[match_h]
                             
                     if not found_assign:
                         # Try Away
                         if a_team in nhl_ref_map:
                             found_assign = nhl_ref_map[a_team]
                         else:
                             match_a = match_team(a_team, nhl_ref_map.keys())
                             if match_a:
                                 found_assign = nhl_ref_map[match_a]
                                 
                     if found_assign:
                         matched_refs = found_assign.get('Officials', [])
                             
                     if matched_refs:
                         ref_impact = nhl_ref_model.get_game_impact(h_team, a_team, matched_refs)
                         log("NHL_REF", f"{h_team} vs {a_team}: Found Refs {matched_refs}. Impact: {ref_impact:+.3f}")
                         
                     m['ref_impact'] = ref_impact
                     m['refs'] = matched_refs

                # --- FATIGUE (Rest Days) ---
                m['home_rest'] = 3 # default
                m['away_rest'] = 3
                 
                h_name_odds = m.get('home_team')
                a_name_odds = m.get('away_team')
                 
                espn_h = match_team(h_name_odds, last_played_map.keys())
                mdt = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00'))
                if espn_h:
                    last_dt = last_played_map[espn_h]
                    delta = mdt - last_dt
                    m['home_rest'] = max(0, delta.days)

                espn_a = match_team(a_name_odds, last_played_map.keys())
                if espn_a:
                    last_dt = last_played_map[espn_a]
                    delta = mdt - last_dt
                    m['away_rest'] = max(0, delta.days)

                # --- NBA REFS ---
                if target_sport == 'NBA':
                    found_ref = None
                    
                    # Try home team first
                    matched_key_h = match_team(h_name_odds, nba_ref_map.keys())
                    if matched_key_h:
                        found_ref = nba_ref_map[matched_key_h]
                    
                    # Try away team if not found
                    if not found_ref:
                        matched_key_a = match_team(a_name_odds, nba_ref_map.keys())
                        if matched_key_a:
                            found_ref = nba_ref_map[matched_key_a]
                            
                    if found_ref:
                        m['ref_1'] = found_ref.get('Crew Chief')
                        m['ref_3'] = found_ref.get('Umpire')
                        
                # --- SOCCER LINEUP IMPACT (Phase 7) ---
                if is_soccer:
                     # For now, only fetch if game starts within 1 hour or is live
                     mdt = datetime.fromisoformat(m['commence_time'].replace('Z', '+00:00'))
                     now = datetime.now(timezone.utc)
                     # Check if game is within 70 mins (lineups usually out 60 mins prior)
                     seconds_until = (mdt - now).total_seconds()
                     
                     if 0 <= seconds_until <= 4200: # 70 mins
                         if 'soccer_client' not in locals():
                             from soccer_client import SoccerClient
                             soccer_client = SoccerClient()
                             
                         # We need Fixture ID. The Odds API doesn't give API-Football Fixture ID.
                         # Challenge: We can't fetch lineups without ID.
                         # Solution: We must use Mapping (OddsAPI Team -> API-Football Fixture).
                         # Too complex for this block.
                         # Fallback: We skip this for V1 unless we have a bridge.
                         pass
                     
                     # Actually, `soccer_client` needs a mapping logic like `news_client`.
                     # Let's check matching logic in `process_markets` later.
                     # For now, initialize placeholder.
                     m['lineup_impact'] = 0.0

                # --- NEWS SENTIMENT IMPACT (New) ---
                # Check for negative news and apply penalty
                if 'news_map' not in locals():
                    from news_client import NewsClient
                    nc_instance = NewsClient()
                    all_news = nc_instance.get_all_news()
                    news_map = {}
                    for n in all_news:
                         # Simple map by team ID if available, otherwise skip for now 
                         # (V2: Text Match Team Name)
                         if n.get('team_id'):
                             tid = str(n.get('team_id'))
                             if tid not in news_map: news_map[tid] = []
                             tid = str(n.get('team_id'))
                             if tid not in news_map: news_map[tid] = []
                             news_map[tid].append(n)
                             
                m['news_impact'] = 0.0
                
                # Logic: Search news for Home/Away team names logic
                # For V1: Check if unique team identifier matches any news item
                
                def get_team_sentiment(team_name, news_list):
                    impact = 0.0
                    if not team_name: return 0.0
                    
                    # Tokenize: "Golden State Warriors" -> ["Golden", "State", "Warriors"]
                    tokens = [t.lower() for t in team_name.split() if len(t) > 3]
                    
                    for n in news_list:
                        headline = n.get('headline', '').lower()
                        desc = n.get('description', '').lower()
                        full = f"{headline} {desc}"
                        
                        # Check if ANY token is in the text
                        if any(token in full for token in tokens):
                            # Found news for this team
                            # Check sentiment
                            # Use weight from News Client (Star vs Role Player)
                            # Default to 0 if not present
                            val = n.get('impact_value', 0.0)
                            
                            # Fallback if news_client returned None
                            if val == 0.0:
                                score = n.get('sentiment_score', 0)
                                if score < 0: val = -0.025
                                elif score > 0: val = 0.01

                            impact += val
                    
                    # Cap impact to avoid overreaction
                    return max(-0.10, min(0.05, impact))

                # Flatten all news for search since we don't have ID map
                flat_news = [item for sublist in news_map.values() for item in sublist]
                
                h_impact = get_team_sentiment(h_name_odds, flat_news)
                a_impact = get_team_sentiment(a_name_odds, flat_news)
                
                # Net Impact for Home Team
                # If Home has bad news (-), News Impact is negative.
                # If Away has bad news (-), News Impact is positive for Home.
                m['news_impact'] = h_impact - a_impact


                        
                # --- REF IMPACT MODEL ---
                # Load Stats if not loaded
                if 'ref_stats_map' not in locals():
                    ref_stats_map = {}
                    try:
                        if os.path.exists("nba_ref_stats_2025_26.csv"):
                            rdf = pd.read_csv("nba_ref_stats_2025_26.csv")
                            for _, row in rdf.iterrows():
                                name = str(row.get('REFEREE', '')).strip()
                                if name:
                                    ref_stats_map[name] = {
                                        'hw': float(row.get('HOME TEAM WIN%', 0.5)),
                                        'fpg': float(row.get('CALLED FOULS PER GAME', 40.0)),
                                        'hfp': float(row.get('FOUL% AGAINST HOME TEAMS', 0.5))
                                    }
                    except Exception as e:
                        print(f"⚠️ Failed to load ref stats: {e}")

                # Load Model if not loaded
                if 'ref_model' not in locals():
                    ref_model = None
                    try:
                        if os.path.exists("models/ref_impact_model.pkl"):
                            ref_model = joblib.load("models/ref_impact_model.pkl")
                    except Exception as e:
                        print(f"⚠️ Failed to load ref model: {e}")

                # Calculate Crew Averages
                crew_stats = {'hw': [], 'fpg': [], 'hfp': []}
                cols = ['ref_1', 'ref_2', 'ref_3']
                for c in cols:
                    r_name = m.get(c)
                    if r_name and r_name in ref_stats_map:
                        s = ref_stats_map[r_name]
                        crew_stats['hw'].append(s['hw'])
                        crew_stats['fpg'].append(s['fpg'])
                        crew_stats['hfp'].append(s['hfp'])
                
                if len(crew_stats['hw']) > 0 and ref_model:
                    avg_hw = sum(crew_stats['hw']) / len(crew_stats['hw'])
                    avg_fpg = sum(crew_stats['fpg']) / len(crew_stats['fpg'])
                    avg_hfp = sum(crew_stats['hfp']) / len(crew_stats['hfp'])
                    
                    # Predict
                    features = [[avg_hw, avg_fpg, avg_hfp]]
                    try:
                        ref_prob = ref_model.predict_proba(features)[0][1]
                        m['ref_impact_prob'] = ref_prob
                        m['ref_edge'] = ref_prob - 0.50 # Deviation from neutral
                    except:
                        pass

                process_markets(
                    m, ratings, calibration, cur, all_opps, target_sport,
                    seen_matches, sharp_data, is_soccer=('soccer' in league),
                    predictions=preds, multipliers=multipliers
                )

                # Fetch exotic markets for select sports
                if sport_key in ['NBA', 'NFL', 'NCAAB', 'NHL'] or 'soccer' in league:
                    try:
                        # Bulk Fetch Exotics (Half markets)
                        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.EXOTIC_MARKETS}"
                        res_ex = requests.get(url, timeout=15).json()
                        if isinstance(res_ex, list):
                            for mx in res_ex:
                                if mx['id'] == m['id']:
                                    process_markets(
                                        mx, ratings, calibration, cur, all_opps, target_sport, 
                                        seen_matches, sharp_data, multipliers=multipliers
                                    )
                    except Exception as e:
                        log("WARN", f"Exotic/Prop fetch failed for {league}: {e}")
                        # Fallback for Exotics logic...
                        try:
                            # Fetch Exotics per event if bulk failed
                            url = f"https://api.the-odds-api.com/v4/sports/{league}/events/{m['id']}/odds?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.EXOTIC_MARKETS}"
                            deep = requests.get(url, timeout=10).json()

                            if 'id' in deep:
                                process_markets(
                                    deep, ratings, calibration, cur, all_opps,
                                    target_sport, seen_matches, sharp_data, is_soccer=False,
                                    multipliers=multipliers
                                )
                        except:
                            pass

        except Exception as e:
            log("ERROR", f"Failed {league}: {e}")

    # Commit database changes
    if cur:
        conn.commit()
        conn.close()

    # Display results
    print(f"\n✅ Scan complete. Found {len(all_opps)} valid bets.")

    if all_opps:
        pd.set_option('display.max_rows', None)
        df = pd.DataFrame(all_opps)
        print("\n🦅 Found Opportunities:")
        print(df[['Sport', 'Event', 'Selection', 'Edge', 'Stake', 'True_Prob']])
        
        # ALERTING SYSTEM
        print("\n🔔 Processing Alerts...")
        for opp in all_opps:
            edge_val = opp.get('Edge_Val', 0)
            
            # Explicit check: Edge >= 1% AND Edge <= 20%
            if 0.01 <= edge_val <= 0.20:
                 # Check Sharp Score (Must be >= 25)
                 sharp_score = opp.get('Sharp_Score', 0)
                 
                 try:
                     s_score = float(sharp_score)
                 except:
                     s_score = 0

                 if s_score >= 25:
                     try:
                        msg = format_opportunity(opp)
                        send_alert(msg)
                        print(f"   📨 Sent alert for {opp['Selection']}")
                     except Exception as e:
                        print(f"   ❌ Alert failed: {e}")
        final_picks = []
        for sport in df['Sport'].unique():
            sport_df = df[df['Sport'] == sport].sort_values(by='Edge_Val', ascending=False)
            final_picks.extend(sport_df.head(3).to_dict('records'))

        # Fill remaining slots up to 15 picks
        if len(final_picks) < 15:
            existing_ids = {f"{p['Event']}{p['Selection']}" for p in final_picks}
            remaining = df[~df.apply(lambda x: f"{x['Event']}{x['Selection']}" in existing_ids, axis=1)]
            final_picks.extend(remaining.sort_values(by='Edge_Val', ascending=False).head(15 - len(final_picks)).to_dict('records'))

        top_15 = pd.DataFrame(final_picks).sort_values(by='Edge_Val', ascending=False).head(15)
        all_bets = df.sort_values(by='Edge_Val', ascending=False)

        cols = ['Date', 'Kickoff', 'Sport', 'Event', 'Selection', 'True_Prob', 'Target', 'Dec_Odds', 'Edge', 'Stake']

        print("\n" + "="*60)
        print("🎯 [TOP 15 PICKS] (Diversity Enforced)")
        print("="*60)
        print(top_15[cols].to_string(index=False))

        print(all_bets[cols].to_string(index=False))

if __name__ == "__main__":
    run_sniper()
