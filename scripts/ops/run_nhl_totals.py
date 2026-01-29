import os
import sys
from datetime import datetime
from config.settings import Config
from pipeline.orchestrator import PipelineContext
from pipeline.stages import init as execute_init
from pipeline.stages import persist as execute_persist
from pipeline.stages.process import execute as execute_process
from pipeline.stages.notify import execute as execute_notify
from utils.logging import log
import argparse
import pandas as pd
import uuid
from scripts.ops.ingest_nhl_live_odds import fetch_nhl_odds
from data.clients.action_network import get_action_network_data
from utils.team_names import normalize_team_name

# Enforce Env
if os.getenv("NHL_TOTALS_V2_ENABLED", "False").lower() != "true":
    log("FATAL", "NHL_TOTALS_V2_ENABLED must be 'true' to run this script.")
    sys.exit(1)

    # Final Cleanup
    if context.db_conn:
        try: context.db_conn.close() 
        except: pass

def run_nhl_totals():
    # CLI Parsing
    parser = argparse.ArgumentParser(description="Run NHL Totals V2 Ops")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--debug_decisions", type=str, default="false")
    parser.add_argument("--dump_raw", type=str, default="false")
    parser.add_argument("--publish", type=str, default="false", help="Publish to Dashboard DB")
    parser.add_argument("--telegram", type=str, default="false", help="Send Telegram Alerts")
    parser.add_argument("--dry_run", type=str, default="false", help="Dry Run mode (Simulates Telegram)")
    parser.add_argument("--out_dir", type=str, default=f"analysis/nhl_phase2_totals/raw_runs/{datetime.now().strftime('%Y-%m-%d')}")
    args, _ = parser.parse_known_args()
    
    log("OPS", f"🚀 Starting NHL Totals Run for {args.date}")
    
    # 1. Setup Context
    context = PipelineContext(
        run_id=f"ops_nhl_v2_{datetime.now().strftime('%H%M%S')}",
        target_sports=["icehockey_nhl"],
        config=Config 
    )
    
    # Inject Dry Run Flag into Config (Runtime Patch)
    if args.dry_run.lower() == "true":
        setattr(context.config, 'TELEGRAM_DRY_RUN', True)
        log("OPS", "⚠️  TELEGRAM DRY RUN ENABLED")

    try:
        # 1.1 InitializeDB & Auth (Required for Persist)
        if not execute_init.execute(context):
             log("FATAL", "Init Stage Failed. Cannot proceed.")
             if context.db_conn: context.db_conn.close()
             sys.exit(1)

             
        # 0. AUTO-INGEST (User Requirement: Odds grabbed on all commands)
        log("OPS", "Triggering Live Odds Ingest...")
        fetch_nhl_odds()
        
        # 0.1 FETCH SHARP DATA (ActionNetwork Parity)
        log("OPS", "Fetching ActionNetwork Sharp Data...")
        try:
            sharp_data = get_action_network_data()
            context.sharp_data = sharp_data
            log("OPS", f"✅ Loaded Sharp Data for {len(sharp_data)} matchups.")
        except Exception as e:
             log("WARN", f"Sharp Data Fetch Failed: {e}")
        
        # 1.5 Load Odds Data (Manual Ingest for Ops)
        live_odds_path = "Hockey Data/nhl_totals_odds_live.csv"
        if os.path.exists(live_odds_path):
            df = pd.read_csv(live_odds_path)
            games = []
            for _, row in df.iterrows():
                 # Construct Bookmakers List (H2H + Totals)
                 bookmakers = []
                 
                 # Totals Market
                 if pd.notna(row['total_line_close']):
                     bookmakers.append({
                         "key": "totals",
                         "title": row['bookmaker'],
                         "markets": [{
                             "key": "totals",
                             "outcomes": [
                                 {"name": "Over", "price": row['over_price_close'], "point": row['total_line_close']},
                                 {"name": "Under", "price": row['under_price_close'], "point": row['total_line_close']}
                             ]
                         }]
                     })
                     
                 # Moneyline Market
                 if pd.notna(row.get('home_moneyline')) and pd.notna(row.get('away_moneyline')):
                     bookmakers.append({
                         "key": "h2h",
                         "title": row['bookmaker'],
                         "markets": [{
                             "key": "h2h",
                             "outcomes": [
                                 {"name": row['home_team'], "price": row['home_moneyline']},
                                 {"name": row['away_team'], "price": row['away_moneyline']}
                             ]
                         }]
                     })

                 # Reconstruct Game Object
                 # USE STABLE ID if available (Critical for Dashboard Deduplication)
                 gid = row.get('game_id')
                 if pd.isna(gid):
                     gid = str(uuid.uuid4()).replace("-", "")[:32]
                     
                 game_obj = {
                     "id": gid, 
                     "home_team": row['home_team'],
                     "away_team": row['away_team'],
                     "commence_time": row.get('commence_time_utc', datetime.now().isoformat()),
                     "sport_key": "icehockey_nhl",
                     "starters": {
                         "home_starter": row.get('home_starter') if pd.notna(row.get('home_starter')) else None,
                         "away_starter": row.get('away_starter') if pd.notna(row.get('away_starter')) else None
                     },
                     "bookmakers": bookmakers
                 }
                 games.append(game_obj)
            
            context.odds_data["icehockey_nhl"] = games
            context.odds_data["NHL"] = games # Compatibility alias
            log("OPS", f"✅ Loaded {len(games)} games from snapshot.")
        else:
            log("WARN", f"Odds Snapshot not found: {live_odds_path}")
        
        # 2. Execute Process Stage (Predictions)
        try:
            success = execute_process(context)
            if not success:
                log("FATAL", "ProcessStage returned False")
                if context.db_conn: context.db_conn.close()
                sys.exit(1)
        except Exception as e:
            log("FATAL", f"Process Error: {e}")
            raise e
                
        # 3. Publish to Dashboard & Telegram (User Requirement: Unified Path)
        # Transform Audit Log to Opportunity Objects compatible with Persist/Notify
        if args.publish.lower() == "true" or args.telegram.lower() == "true" or args.dry_run.lower() == "true":
            log("OPS", "Processing V2 Opportunities for Downstream Publishing...")
            context.opportunities = [] # Clear any partials
            
            audit_log = context.metadata.get('nhl_audit_log', [])
            if len(audit_log) > 0:
                pass # No debug logs here
            
            for row in audit_log:
                if row.get('decision') == 'RECOMMEND':
                    # Construct Canonical Opportunity Object
                    side = row['bet_side'] # OVER/UNDER
                    line = row['total_line']
                    sel = f"{side} {line}"
                    price = row['over_price'] if side == 'OVER' else row['under_price']
                    prob = row['prob_over'] if side == 'OVER' else row['prob_under']
                    
                    # Sharp Data Lookup
                    m_pct, t_pct = 0, 0
                    try:
                        # Key Format: "away @ home" (Normalized)
                        # V2 Trace has raw names
                        n_home = normalize_team_name(row['home_team'])
                        n_away = normalize_team_name(row['away_team'])
                        matchup_key = f"{n_away} @ {n_home}"
                        
                        market_type = 'total' # Default for Totals V2 recommendation
                        side_key = side.strip().title() # OVER -> Over, UNDER -> Under
                        
                        # Check context.sharp_data
                        # Structure: data[matchup_key][market_type][side_key] = {'money': X, 'tickets': Y}
                        
                        match_data = context.sharp_data.get(matchup_key, {})
                        market_data = match_data.get(market_type, {})
                        split = market_data.get(side_key, {})
                        
                        m_pct = split.get('money', 0)
                        t_pct = split.get('tickets', 0)
                        
                        if m_pct > 0 or t_pct > 0:
                             log("DEBUG", f"Found Sharp Split for {matchup_key} {side}: ${m_pct}% T{t_pct}%")
                             
                    except Exception as e:
                        # Non-fatal lookup failure
                        pass

                    opp = {
                        "unique_id": f"{row['game_id']}_totals_{side.lower()}", # Deterministic ID
                        "run_id": context.run_id,
                        "Kickoff": row['commence_time'],
                        "Sport": "icehockey_nhl",
                        "Event": f"{row['home_team']} vs {row['away_team']}",
                        "Selection": sel,
                        "Dec_Odds": float(price),
                        "True_Prob": float(prob),
                        "Edge_Val": float(row['ev']),
                        "raw_stake": 1.0, # Standard Unit
                        "trigger_type": "model_v2",
                        "teams": f"{row['away_team']} @ {row['home_team']}", # Format for Notify
                        "metadata": row,
                        "money_pct": m_pct,
                        "ticket_pct": t_pct 
                    }
                    context.opportunities.append(opp)
            
            log("OPS", f"Generated {len(context.opportunities)} Opportunities for Publishing.")

            # 3.1 Persist (Dashboard)
            if args.publish.lower() == "true":
                log("OPS", "Executing Dashboard Persistence...")
                persist_success = execute_persist.execute(context)
                if persist_success:
                    log("OPS", "✅ Published to Dashboard DB.")
                else:
                    log("WARN", "Dashboard Publish Failed.")
            
            # 3.2 Notify (Telegram)
            if args.telegram.lower() == "true" or args.dry_run.lower() == "true":
                log("OPS", "Executing Telegram Notification...")
                execute_notify(context)

        # 4. Save Artifacts Deterministically (Ops Audit)
        output_dir = f"predictions/nhl_totals_v2/{args.date}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Recommendations
        if context.opportunities:
            df = pd.DataFrame(context.opportunities)
            # Filter cols if needed, or dump all
            if not df.empty:
                df.to_csv(f"{output_dir}/recommendations.csv", index=False)
                log("OPS", f"✅ Saved {len(df)} recommendations to {output_dir}/recommendations.csv")
            
        # RAW DUMP (CLI Requested)
        if args.dump_raw.lower() == "true":
            log("OPS", "Generating Raw Decision Trace...")
            audit_log = context.metadata.get('nhl_audit_log', [])
            
            if audit_log:
                os.makedirs(args.out_dir, exist_ok=True)
                df = pd.DataFrame(audit_log)
                
                # Ensure columns exist
                cols = [
                    'game_id', 'date', 'home_team', 'away_team', 'commence_time',
                    'total_line', 'over_price', 'under_price',
                    'implied_over', 'implied_under',
                    'expected_total', 'sigma', 'bias_applied',
                    'prob_over', 'prob_under',
                    'ev_over', 'ev_under',
                    'longshot_cap_pass',
                    'bet_side', 'decision', 'reject_reasons'
                ]
                
                # Fill missing
                for c in cols:
                    if c not in df.columns:
                        df[c] = None
                        
                # Export
                out_path = f"{args.out_dir}/decisions_raw.csv"
                df[cols].to_csv(out_path, index=False)
                log("OPS", f"✅ Raw Dump Saved: {out_path}")
                
                # Print to Console (Proof Check)
                pd.set_option('display.max_columns', None)
                pd.set_option('display.width', 1000)
                print("\n=== RAW DECISION TRACE ===")
                print(df[cols].to_string())
                print("==========================\n")
            else:
                log("WARN", "No Audit Log found in metadata.")
                
            # DUMP MONEYLINE TRACE
            ml_log = context.metadata.get('nhl_ml_audit_log', [])
            if ml_log:
                df_ml = pd.DataFrame(ml_log)
                
                ml_cols = [
                    'game_id', 'date', 'home_team', 'away_team',
                    'home_odds', 'away_odds',
                    'prob_home', 'prob_away',
                    'ev_home', 'ev_away',
                    'bet_side', 'decision', 'reject_reasons',
                    'home_abbr', 'away_abbr'
                ]
                
                # Fill missing
                for c in ml_cols:
                    if c not in df_ml.columns:
                        df_ml[c] = None
                        
                out_path_ml = f"{args.out_dir}/decisions_moneyline_raw.csv"
                df_ml[ml_cols].to_csv(out_path_ml, index=False)
                log("OPS", f"✅ Moneyline Trace Saved: {out_path_ml}")
                
                pd.set_option('display.max_columns', None)
                print("\n=== RAW DECISION TRACE (MONEYLINE) ===")
                print(df_ml[ml_cols].to_string())
                print("======================================\n")
            else:
                 log("WARN", "No Moneyline Audit Log found in metadata.")
                
    except Exception as e:
        log("FATAL", f"Run Failed: {e}")
        if context.db_conn:
            try: context.db_conn.close() 
            except: pass
        sys.exit(1)
    
    # Final Cleanup
    if context.db_conn:
        try: context.db_conn.close() 
        except: pass

if __name__ == "__main__":
    run_nhl_totals()
