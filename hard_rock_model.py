"""
Philly P Sniper - Automated Sports Betting Intelligence System

Main orchestrator that coordinates all modules to identify profitable betting opportunities.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

from config import Config
from utils import log
from database import get_db, init_db, get_calibration
from bet_grading import settle_pending_bets
from ratings import get_team_ratings
from api_clients import get_action_network_data, get_soccer_predictions, get_nhl_player_stats
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
            res = requests.get(url, timeout=15).json()

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

            # Process each match
            seen_matches = set()
            for m in matches:
                process_markets(
                    m, ratings, calibration, cur, all_opps, target_sport,
                    seen_matches, sharp_data, is_soccer=('soccer' in league),
                    predictions=preds, multipliers=multipliers
                )

                # Fetch exotic markets for select sports
                if sport_key in ['NBA', 'NFL', 'NCAAB', 'NHL'] or 'soccer' in league:
                    try:
                        # Bulk Fetch Exotics (Half markets)
                        # Do NOT include props here as it breaks the bulk endpoint
                        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.EXOTIC_MARKETS}"
                        res_ex = requests.get(url, timeout=15).json()
                        if isinstance(res_ex, list):
                            for mx in res_ex:
                                if mx['id'] == m['id']:
                                    process_markets(
                                        mx, ratings, calibration, cur, all_opps, target_sport, 
                                        seen_matches, sharp_data, multipliers=multipliers
                                    )

                        # Explicitly Fetch NHL Props via Event Endpoint (Required)
                        if sport_key == 'NHL' and nhl_player_stats:
                            prop_url = f"https://api.the-odds-api.com/v4/sports/{league}/events/{m['id']}/odds?apiKey={Config.ODDS_API_KEY}&regions=us,us2&markets={Config.PROP_MARKETS}"
                            prop_res = requests.get(prop_url, timeout=10).json()
                            
                            # DEBUG RESPONSE
                            if 'bookmakers' not in prop_res:
                                print(f"   ⚠️ [DEBUG] Props missing for {m['id']}. Resp: {list(prop_res.keys())}")
                            
                            if 'bookmakers' in prop_res:
                                # DISABLED (User Request v280): Settlement logic needs tuning. Architecture preserved.
                                # process_nhl_props(
                                #    prop_res, prop_res, nhl_player_stats, calibration, cur, all_opps, seen_matches
                                # )
                                pass

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

        # Select top 3 per sport for diversity
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

        print("\n" + "="*60)
        print("📜 [ALL RECOMMENDED BETS]")
        print("="*60)
        print(all_bets[cols].to_string(index=False))

if __name__ == "__main__":
    run_sniper()
