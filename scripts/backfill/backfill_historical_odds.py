import requests
from config import Config
from database import get_db
import pandas as pd
from datetime import datetime
import time
import difflib

# Mapping DB League -> Odds API Key
LEAGUE_MAP = {
    'EPL': 'soccer_epl',
    'La_liga': 'soccer_spain_la_liga',
    'Bundesliga': 'soccer_germany_bundesliga',
    'Serie_A': 'soccer_italy_serie_a',
    'Ligue_1': 'soccer_france_ligue_one'
}

def normalize_name(name):
    name = name.lower()
    replacements = {
        'manchester united': 'man utd',
        'manchester city': 'man city',
        'tottenham hotspur': 'tottenham',
        'paris saint germain': 'psg',
        'paris sg': 'psg',
        'brighton & hove albion': 'brighton',
        'wolverhampton wanderers': 'wolves',
        'wolverhampton': 'wolves',
        'leverkusen': 'bayer leverkusen',
        'monchengladbach': 'borussia monchengladbach',
        'inter': 'internazionale',
        'ac milan': 'milan',
        'atl. madrid': 'atletico madrid',
        'ath bilbao': 'athletic bilbao'
    }
    for k, v in replacements.items():
        if k in name:
            name = name.replace(k, v)
    return name.strip()

def backfill_odds():
    conn = get_db()
    if not conn:
        print("❌ DB Connection Failed")
        return

    # 1. Get matches needing odds (Base Query)
    # We select ALL matches for the leagues to check if they have odds logic locally
    # Or rely on the query to filter.
    query = """
        SELECT match_id, league, date, home_team, away_team, odds_over_2_5 
        FROM matches 
        WHERE league IN ('EPL', 'La_liga', 'Bundesliga', 'Serie_A', 'Ligue_1')
        ORDER BY date DESC
    """
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("✅ No matches found.")
        return

    # Group by (league, date)
    df['date_str'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    groups = df.groupby(['league', 'date_str'])
    
    print(f"🔄 Found {len(df)} matches in {len(groups)} distinct league-day groups.")
    
    processed_count = 0
    skipped_count = 0
    updates = []
    
    for (league, date_str), group_df in groups:
        sport_key = LEAGUE_MAP.get(league)
        if not sport_key: continue
        
        # IDEMPOTENCY CHECK
        # Check if ANY match in this group already has odds logged in DB
        # Since we queried `odds_over_2_5`, we can check the DataFrame slice directly
        # If > 0 matches in this group have odds_over_2_5 != None, we assume date is processed.
        # This prevents re-fetching partial days.
        existing_odds_count = group_df['odds_over_2_5'].count() # counts non-null
        if existing_odds_count > 0:
            # print(f"⏭️ Skipping {sport_key} on {date_str} (Already has data)")
            skipped_count += 1
            processed_count += 1
            continue
            
        # timestamp for API
        snapshot_iso = f"{date_str}T10:00:00Z"
        print(f"📡 {processed_count+1}/{len(groups)} Fetching {sport_key} for {date_str}...")
        
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds-history"
        params = {
            'apiKey': Config.ODDS_API_KEY,
            'regions': 'us',
            'markets': 'totals',
            'date': snapshot_iso,
            'oddsFormat': 'decimal'
        }
        
        try:
            res = requests.get(url, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                events = data.get('data', [])
                
                # Match internal matches to API events
                for idx, row in group_df.iterrows():
                    h_name = normalize_name(row['home_team'])
                    a_name = normalize_name(row['away_team'])
                    
                    best_event = None
                    best_score = 0
                    
                    for ev in events:
                        api_h = normalize_name(ev['home_team'])
                        api_a = normalize_name(ev['away_team'])
                        score_h = difflib.SequenceMatcher(None, h_name, api_h).ratio()
                        score_a = difflib.SequenceMatcher(None, a_name, api_a).ratio()
                        avg_score = (score_h + score_a) / 2
                        
                        if avg_score > 0.8 and avg_score > best_score:
                            best_score = avg_score
                            best_event = ev
                    
                    if best_event:
                        books = best_event.get('bookmakers', [])
                        target_book = next((b for b in books if b['key'] in ['draftkings', 'fanduel', 'bovada', 'betmgm']), None) or (books[0] if books else None)
                        
                        if target_book:
                            totals = next((m for m in target_book.get('markets', []) if m['key'] == 'totals'), None)
                            if totals:
                                line_25 = next((x for x in totals['outcomes'] if abs(x.get('point', 0) - 2.5) < 0.1 and x['name'] == 'Over'), None)
                                
                                o_price = 0.0
                                u_price = 0.0
                                point = 0.0
                                
                                if line_25:
                                    o_price = line_25['price']
                                    u_price = next((x['price'] for x in totals['outcomes'] if abs(x.get('point', 0) - 2.5) < 0.1 and x['name'] == 'Under'), 0.0)
                                    point = 2.5
                                else:
                                    try:
                                        first = totals['outcomes'][0]
                                        point = first.get('point')
                                        name = first['name']
                                        price = first['price']
                                        o_price = price if name == 'Over' else next((x['price'] for x in totals['outcomes'] if x['name'] == 'Over'), 0.0)
                                        u_price = price if name == 'Under' else next((x['price'] for x in totals['outcomes'] if x['name'] == 'Under'), 0.0)
                                    except:
                                        continue

                                updates.append({
                                    'match_id': row['match_id'],
                                    'odds_over': o_price,
                                    'odds_under': u_price,
                                    'line': point
                                })

            elif res.status_code == 429:
                print("⚠️ Rate Limit Exceeded (429). Sleeping 5s...")
                time.sleep(5)
            else:
                print(f"⚠️ API Error {res.status_code}: {res.text}")

        except Exception as e:
            print(f"Error calling API: {e}")
            
        processed_count += 1
        time.sleep(0.3) 
        
        # Batch Commit Logic
        if len(updates) > 50 or (processed_count % 10 == 0 and updates):
            print(f"💾 Committing batch of {len(updates)} updates (Progress: {processed_count}/{len(groups)})...")
            cur = conn.cursor()
            for u in updates:
                cur.execute("""
                    UPDATE matches 
                    SET closing_total = %s, market_avg_over = %s, market_avg_under = %s
                    WHERE match_id = %s
                """, (u['line'], u['odds_over'], u['odds_under'], u['match_id']))
                
                if abs(u['line'] - 2.5) < 0.1:
                    cur.execute("""
                        UPDATE matches 
                        SET odds_over_2_5 = %s, odds_under_2_5 = %s
                        WHERE match_id = %s
                    """, (u['odds_over'], u['odds_under'], u['match_id']))
            conn.commit()
            cur.close()
            updates = [] # Reset buffer

    # Final Commit
    if updates:
        print(f"💾 Committing final batch of {len(updates)} updates...")
        cur = conn.cursor()
        for u in updates:
            cur.execute("""
                UPDATE matches 
                SET closing_total = %s, market_avg_over = %s, market_avg_under = %s
                WHERE match_id = %s
            """, (u['line'], u['odds_over'], u['odds_under'], u['match_id']))
            if abs(u['line'] - 2.5) < 0.1:
                cur.execute("""
                    UPDATE matches 
                    SET odds_over_2_5 = %s, odds_under_2_5 = %s
                    WHERE match_id = %s
                """, (u['odds_over'], u['odds_under'], u['match_id']))
        conn.commit()
        cur.close()
        
    conn.close()
    print(f"✅ Backfill Complete. Skipped {skipped_count} existing groups.")

if __name__ == "__main__":
    backfill_odds()
