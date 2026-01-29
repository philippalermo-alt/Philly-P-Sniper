
import requests
import json
import time
from db.connection import get_db

# NHL API Goalies
# https://api.nhle.com/stats/rest/en/goalie/summary
# ?isAggregate=false&isGame=true&cayenneExp=seasonId=...

SEASONS = [20222023, 20232024, 20242025, 20252026]

def ingest_goalies():
    print("🥅 Ingesting Goalie History...")
    conn = get_db()
    cur = conn.cursor()
    
    for season in SEASONS:
        print(f"Fetching Season {season}...")
        start = 0
        limit = 100
        
        while True:
            url = f"https://api.nhle.com/stats/rest/en/goalie/summary?isAggregate=false&isGame=true&start={start}&limit={limit}&cayenneExp=seasonId={season}%20and%20gameTypeId=2"
            
            try:
                res = requests.get(url)
                payload = res.json()
                data = payload.get('data', [])
                total = payload.get('total', 0)
                
                if not data:
                    break
                
                print(f"  Fetched {len(data)} rows (Start {start} / Total {total})...")
                
                rows = []
                for r in data:
                    gid = str(r['gameId'])
                    pid = r['playerId']
                    name = r.get('goalieFullName')
                    team = r.get('teamAbbrev')
                    opp = r.get('opponentTeamAbbrev')
                    date = r.get('gameDate')
                    
                    started = (r.get('gamesStarted', 0) > 0)
                    toi = int(r.get('timeOnIce', 0))
                    sa = r.get('shotsAgainst', 0)
                    ga = r.get('goalsAgainst', 0)
                    saves = r.get('saves', 0)
                    sv_pct = r.get('savePct')
                    
                    rows.append((gid, team, opp, pid, name, date, started, toi, sa, ga, saves, sv_pct))
                    
                # Upsert
                sql = """
                INSERT INTO public.nhl_goalie_game_logs
                (game_id, team, opponent, goalie_id, goalie_name, game_date, 
                 is_starter, toi_seconds, shots_against, goals_against, saves, save_pct)
                VALUES %s
                ON CONFLICT (game_id, goalie_id) DO UPDATE SET
                is_starter=EXCLUDED.is_starter, toi_seconds=EXCLUDED.toi_seconds,
                shots_against=EXCLUDED.shots_against, goals_against=EXCLUDED.goals_against,
                saves=EXCLUDED.saves, save_pct=EXCLUDED.save_pct
                """
                
                from psycopg2.extras import execute_values
                if rows:
                    execute_values(cur, sql, rows)
                    conn.commit()
                
                start += limit
                if start >= total:
                    break
                
                time.sleep(0.5) 
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                break
            
    conn.close()
    print("🥅 Goalie Ingestion Complete.")

if __name__ == "__main__":
    ingest_goalies()
