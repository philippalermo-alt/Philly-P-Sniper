from pipeline.orchestrator import PipelineContext
from utils.logging import log
from datetime import datetime

def execute(context: PipelineContext) -> bool:
    """
    Stage 5: Persistence
    - Commit Database Transaction
    - Update Heartbeat
    - Batch Execute Operations
    """
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
                    op.get('home_tempo', 0), op.get('away_tempo', 0)
                )
                
                sql = """
                    INSERT INTO intelligence_log
                    (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, stake, trigger_type, closing_odds, ticket_pct, money_pct, sharp_score, home_rest, away_rest, ref_1, ref_2, ref_3, 
                    home_adj_em, away_adj_em, home_adj_o, away_adj_o, home_adj_d, away_adj_d, home_tempo, away_tempo)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (event_id) DO UPDATE SET
                        odds=EXCLUDED.odds, true_prob=EXCLUDED.true_prob, edge=EXCLUDED.edge,
                        stake=EXCLUDED.stake, selection=EXCLUDED.selection, timestamp=EXCLUDED.timestamp,
                        trigger_type=EXCLUDED.trigger_type,
                        sharp_score=EXCLUDED.sharp_score,
                        ticket_pct=EXCLUDED.ticket_pct, money_pct=EXCLUDED.money_pct,
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
                try:
                    tp = float(op['True_Prob'])
                    unique_id = op['unique_id']
                    bucket_c = f"{int(tp * 20) * 5}-{int(tp * 20) * 5 + 5}%"
                    sql_calib = "INSERT INTO calibration_log (event_id, timestamp, predicted_prob, bucket) VALUES (%s, NOW(), %s, %s)"
                    cur.execute(sql_calib, (unique_id, tp, bucket_c))
                except:
                    pass

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
