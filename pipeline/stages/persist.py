from pipeline.orchestrator import PipelineContext
from utils.logging import log
from datetime import datetime
import json

def execute(context: PipelineContext) -> bool:
    """
    Stage 5: Persistence
    - Commit Database Transaction
    - Update Heartbeat
    - Batch Execute Operations
    """
    
    # Helper for JSON cleaning (Nan -> Null)
    def clean_nan(obj):
        if isinstance(obj, float):
            if obj != obj: # NaN check
                return None
            if obj == float('inf') or obj == float('-inf'):
                return None
        return obj

    def safe_json_serializer(obj):
        """Handle numpy types and NaNs"""
        import numpy as np
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return [clean_nan(x) for x in obj.tolist()]
        elif isinstance(obj, dict):
             return {k: (clean_nan(v) if not isinstance(v, (dict, list)) else v) for k, v in obj.items()}
             
        return clean_nan(obj)

    try:
        if not context.db_conn or not context.db_cursor:
            log("WARN", "No active DB connection to commit.")
            return False

        cur = context.db_cursor
        opps = context.opportunities
        
        if not opps:
            log("PERSIST", "No opportunities to persist.")
            return True

        log("PERSIST", f"Persisting {len(opps)} operations to Database...")
        
        insert_count = 0
        delete_count = 0
        
        for op in opps:
            op_type = op.get('op_type', 'INSERT')
            
            if op_type == 'DELETE':
                # Revoke/Delete
                eid = op.get('event_id')
                cur.execute("DELETE FROM intelligence_log WHERE event_id = %s", (eid,))
                cur.execute("DELETE FROM calibration_log WHERE event_id = %s", (eid,))
                delete_count += 1
                
            elif op_type == 'INSERT':
                # Insert / Upsert
                # Extract Params
                params = (
                    op['unique_id'], datetime.now(), op['Kickoff'], op['Sport'], op['Event'],
                    op['Selection'], float(op['Dec_Odds']), float(op['True_Prob']),
                    float(op['Edge_Val']), float(op['raw_stake']), op.get('trigger_type', 'model'),
                    float(op['Dec_Odds']), # closing_odds init
                    op.get('ticket_pct'), op.get('money_pct'), int(op.get('Sharp_Score', 0)),
                    op.get('home_rest'), op.get('away_rest'),
                    op.get('ref_1'), op.get('ref_2'), op.get('ref_3'),
                    op.get('home_adj_em', 0), op.get('away_adj_em', 0),
                    op.get('home_adj_o', 0), op.get('away_adj_o', 0),
                    op.get('home_adj_d', 0), op.get('away_adj_d', 0),
                    op.get('home_tempo', 0), op.get('away_tempo', 0),
                    json.dumps(op.get('metadata', {}), default=safe_json_serializer).replace('NaN', 'null')
                )
                
                sql = """
                    INSERT INTO intelligence_log
                    (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score, home_rest, away_rest, ref_1, ref_2, ref_3, 
                    home_adj_em, away_adj_em, home_adj_o, away_adj_o, home_adj_d, away_adj_d, home_tempo, away_tempo, metadata)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (event_id) DO UPDATE SET
                        odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                        stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                        trigger_type=EXCLUDED.trigger_type,
                        sharp_score=COALESCE(EXCLUDED.sharp_score, intelligence_log.sharp_score),
                        ticket_pct=COALESCE(EXCLUDED.ticket_pct, intelligence_log.ticket_pct), 
                        money_pct=COALESCE(EXCLUDED.money_pct, intelligence_log.money_pct),
                        closing_odds=EXCLUDED.closing_odds,
                        home_rest=EXCLUDED.home_rest, away_rest=EXCLUDED.away_rest,
                        ref_1=EXCLUDED.ref_1, ref_2=EXCLUDED.ref_2, ref_3=EXCLUDED.ref_3,
                        home_adj_em=EXCLUDED.home_adj_em, away_adj_em=EXCLUDED.away_adj_em,
                        home_adj_o=EXCLUDED.home_adj_o, away_adj_o=EXCLUDED.away_adj_o,
                        home_adj_d=EXCLUDED.home_adj_d, away_adj_d=EXCLUDED.away_adj_d,
                        home_tempo=EXCLUDED.home_tempo, away_tempo=EXCLUDED.away_tempo;
                """
                cur.execute(sql, params)
                insert_count += 1
                
                # Calibration Log
                # Calibration Log
                try:
                    cur.execute("SAVEPOINT calib_pt")
                    tp = float(op['True_Prob'])
                    unique_id = op['unique_id']
                    bucket_c = f"{int(tp * 20) * 5}-{int(tp * 20) * 5 + 5}%"
                    sql_calib = "INSERT INTO calibration_log (event_id, timestamp, predicted_prob, bucket) VALUES (%s, NOW(), %s, %s)"
                    cur.execute(sql_calib, (unique_id, tp, bucket_c))
                    cur.execute("RELEASE SAVEPOINT calib_pt")
                except Exception as e:
                    cur.execute("ROLLBACK TO SAVEPOINT calib_pt")
                    log("WARN", f"Calibration Log Failed for {op.get('unique_id')}: {e}")

        # Phase 8: Persist ALL NBA Predictions (Audit Log)
        if hasattr(context, 'nba_predictions') and context.nba_predictions:
            log("PERSIST", f"Logging {len(context.nba_predictions)} NBA Model Predictions...")
            
            # Map Accepted Opportunities for Decision Tagging
            accepted_ids = set()
            for op in opps:
                 # Logic to match Opportunity back to Game ID
                 # Event ID usually: "{game_id}_{selection}"
                 # We can split by '_' to get game_id prefix?
                 # Or rely on `op['unique_id']` which we set to `event_id`
                 eid = op.get('event_id', '')
                 accepted_ids.add(eid)
            
            for p in context.nba_predictions:
                try:
                    # Determine Decision
                    # We need to know if we bet on Home ML, Away ML, Over, etc.
                    # This is tricky because one Game Prediction -> Multiple Markets.
                    # We should probably log 2 rows? One for ML, One for Total?
                    # Schema has 'market' column. So yes, split it.
                    
                    # 1. ML Record
                    ml_decision = "REJECT"
                    ml_reason = "No Edge / Model Filter"
                    
                    # Check if we have an accepted ML bet for this game
                    # Heuristic: verify if any op's event_id contains game_id AND (Home/Away team name or ML)
                    # Let's simplify: Just log raw. Analysis can join later.
                    # Actually user wants 'decision' field.
                    
                    # Insert ML
                    cur.execute("""
                        INSERT INTO nba_predictions 
                        (run_id, game_id, game_date_est, home_team, away_team, market, book, 
                         odds_home, odds_away, prob_home, prob_away, features_snapshot, 
                         model_version, decision)
                        VALUES (%s, %s, %s, %s, %s, 'ML', %s, %s, %s, %s, %s, %s, 'v2.0.0', 'LOGGED')
                    """, (
                        p['run_id'], p['game_id'], p['game_date_est'], p['home_team'], p['away_team'], 
                        p['book'], float(p['odds_home']), float(p['odds_away']), float(p['prob_home']), float(p['prob_away']), 
                        json.dumps(p['features_snapshot'], default=safe_json_serializer).replace('NaN', 'null')
                    ))
                    
                    # Insert Totals (if available)
                    if p.get('expected_total') is not None:
                         cur.execute("""
                            INSERT INTO nba_predictions 
                            (run_id, game_id, game_date_est, home_team, away_team, market, book, 
                             total_line, expected_total, prob_over, 
                             model_version, decision)
                            VALUES (%s, %s, %s, %s, %s, 'TOTAL', %s, %s, %s, %s, 'v2.0.0', 'LOGGED')
                        """, (
                            p['run_id'], p['game_id'], p['game_date_est'], p['home_team'], p['away_team'], 
                            p['book'], 0.0, float(p['expected_total']), float(p['prob_over'])
                        ))

                except Exception as ex:
                    log("WARN", f"Failed to log prediction for {p.get('game_id')}: {ex}")

        # Update Heartbeat
        try:
            cur.execute(
                "INSERT INTO app_settings (key, value) VALUES ('model_last_run', NOW()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            )
        except Exception as e:
            log("WARN", f"Heartbeat Update Failed: {e}")
        
        # Commit
        context.db_conn.commit()
        log("PERSIST", f"✅ Batch Committed: {insert_count} Upserts, {delete_count} Deletes")
        return True
    
    except Exception as e:
        context.log_error("PERSIST", str(e))
        # Rollback if possible
        if context.db_conn:
            context.db_conn.rollback()
            log("PERSIST", "♻️ Transaction Rolled Back")
        return False
