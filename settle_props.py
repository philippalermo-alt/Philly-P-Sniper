import requests
import difflib
import time
from datetime import datetime, timedelta
import pytz
from database import get_db, safe_execute
from utils import log

# Configuration
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard"
ESPN_SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/summary"

def get_espn_games(date_str):
    """Fetch completed games for a specific date (YYYY-MM-DD)."""
    try:
        url = f"{ESPN_SCOREBOARD}?dates={date_str.replace('-', '')}"
        res = requests.get(url, timeout=10).json()
        games = []
        for ev in res.get('events', []):
            status = ev['status']['type']['state']
            if status == 'post': # Completed
                comp = ev['competitions'][0]
                games.append({
                    'id': ev['id'],
                    'home': comp['competitors'][0]['team']['displayName'],
                    'away': comp['competitors'][1]['team']['displayName'],
                    'date': date_str
                })
        return games
    except Exception as e:
        log("ERROR", f"ESPN Fetch failed: {e}")
        return []

def get_player_stats(http_calls, game_id):
    """Fetch SOG stats for all players in a game."""
    # Rate limit guard
    if http_calls > 0: time.sleep(0.5)
    
    stats = {}
    try:
        url = f"{ESPN_SUMMARY}?event={game_id}"
        res = requests.get(url, timeout=10).json()
        
        box = res.get('boxscore', {})
        for team in box.get('teams', []):
            for player in team.get('statistics', []):
                # NHL stats usually in 'statistics' array
                # But ESPN structure determines if this is 'skaters' or 'goalies'
                # Usually: team['players'] -> list of players -> stats
                pass 
                
        # Correct parsing for ESPN NHL Boxscore
        # boxscore -> players -> [ { team, statistics: [ { name: "skaters", athletes: [...] } ] } ]
        if 'players' in box:
            for team_group in box['players']:
                for stat_group in team_group.get('statistics', []):
                    if stat_group['name'] == 'skaters':
                        for athlete in stat_group.get('athletes', []):
                            name = athlete['athlete']['displayName']
                            # Find SOG in stats (format varies, usually "shots")
                            # stats array corresponds to labels.
                            # We need to find the index of "S" or "SOG"
                            keys = stat_group.get('keys', []) # e.g. ["G", "A", "Pts", "+/-", "PIM", "SOG", "HITS", "BLKS", "TOI"]
                            try:
                                sog_idx = keys.index('S') # ESPN often uses 'S' or 'Sh'
                            except ValueError:
                                try:
                                    sog_idx = keys.index('Sh')
                                except ValueError:
                                    continue
                                    
                            if sog_idx < len(athlete['stats']):
                                sog = int(athlete['stats'][sog_idx])
                                stats[name] = sog
                                
    except Exception as e:
        print(f"Error parsing stats for {game_id}: {e}")
        
    return stats

def settle_props():
    print("🏒 Starting NHL Prop Settlement...")
    conn = get_db()
    if not conn: return
    
    cur = conn.cursor()
    
    # 1. Fetch PENDING props
    cur.execute("""
        SELECT event_id, selection, teams, kickoff 
        FROM intelligence_log 
        WHERE outcome = 'PENDING' 
        AND (sport = 'NHL_PROP' OR selection LIKE '%SOG')
        AND kickoff < NOW() - INTERVAL '4 HOURS'
    """)
    props = cur.fetchall()
    
    if not props:
        print("✅ No pending props to settle.")
        return

    print(f"🔍 Found {len(props)} pending props.")
    
    # Group by Date to minimize API calls
    # Key: Date -> [Bets]
    grouped_by_date = {}
    for p in props:
        # p[3] is kickoff timestamp. Convert to US/Eastern date string
        dt_est = p[3].astimezone(pytz.timezone('US/Eastern'))
        date_str = dt_est.strftime('%Y-%m-%d')
        if date_str not in grouped_by_date: grouped_by_date[date_str] = []
        grouped_by_date[date_str].append(p)
        
    for date_str, bets in grouped_by_date.items():
        print(f"📅 Processing {date_str}...")
        games = get_espn_games(date_str)
        
        # Match matches
        game_stats_cache = {} # game_id -> player_stats
        
        for bet in bets:
            eid, sel, teams_str, _ = bet
            
            # Match game
            # teams_str e.g. "Flyers @ Penguins"
            try:
                away_b, home_b = teams_str.split(' @ ')
            except:
                continue
                
            matched_game = None
            for g in games:
                # Fuzzy match names
                h_rat = difflib.SequenceMatcher(None, home_b, g['home']).ratio()
                a_rat = difflib.SequenceMatcher(None, away_b, g['away']).ratio()
                if h_rat > 0.6 and a_rat > 0.6:
                    matched_game = g
                    break
            
            if not matched_game:
                print(f"⚠️ Could not match game: {teams_str} on {date_str}")
                continue
                
            gid = matched_game['id']
            if gid not in game_stats_cache:
                game_stats_cache[gid] = get_player_stats(1, gid)
                
            stats = game_stats_cache[gid]
            if not stats:
                continue
                
            # Parse Selection: "Player Name Over/Under X.5 SOG"
            try:
                parts = sel.split(' ')
                # structure: [First, Last, ..., Over/Under, Line, SOG]
                # Find "Over" or "Under" index
                if "Over" in parts:
                    type_idx = parts.index("Over")
                    bet_type = "Over"
                elif "Under" in parts:
                    type_idx = parts.index("Under")
                    bet_type = "Under"
                else:
                    continue
                    
                player_name_bet = " ".join(parts[:type_idx])
                line = float(parts[type_idx+1])
                
                # Fuzzy match player name
                best_match = difflib.get_close_matches(player_name_bet, stats.keys(), n=1, cutoff=0.7)
                if not best_match:
                    print(f"❌ Player mismatch: {player_name_bet}")
                    continue
                    
                actual_sog = stats[best_match[0]]
                
                # Grade
                outcome = None
                if bet_type == "Over":
                    outcome = 'WON' if actual_sog > line else 'LOST'
                else:
                    outcome = 'WON' if actual_sog < line else 'LOST'
                    
                # Update DB
                print(f"✅ Grading {sel}: Actual {actual_sog} -> {outcome}")
                cur.execute("UPDATE intelligence_log SET outcome = %s WHERE event_id = %s", (outcome, eid))
                
            except Exception as e:
                print(f"Error grading {sel}: {e}")
                
    conn.commit()
    cur.close()
    conn.close()
    print("🏁 Settlement Complete.")

if __name__ == "__main__":
    settle_props()
