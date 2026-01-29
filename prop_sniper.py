from config import Config
from utils import log
from db.connection import get_db
from data.clients.odds_api import fetch_prop_odds
from player_props_model import PlayerPropsPredictor
import pandas as pd
from datetime import datetime
import time
import math
from lineup_client import get_confirmed_lineup, normalize_name

class PropSniper:
    """
    Automated engine to:
    1. Fetch upcoming matchups.
    2. Pull Prop Odds (Goalscorer, Shots) from API.
    3. Run PlayerPropsModel (Poisson).
    4. Calculate Edge.
    5. Log +EV bets to Intelligence Log.
    """
    
    def __init__(self):
        self.min_edge = 0.02 # 2% Edge min
        self.min_minutes = 400 # Reliability check
        self.leagues = [
            ("EPL", "soccer_epl"),
            ("La_liga", "soccer_spain_la_liga"),
            ("Bundesliga", "soccer_germany_bundesliga"),
            ("Serie_A", "soccer_italy_serie_a"),
            ("Ligue_1", "soccer_france_ligue_one"),
            ("Champions_League", "soccer_uefa_champs_league"),
            ("Europa_League", "soccer_uefa_europa_league")
        ]
        self.lineup_cache = {} # Cache match_id -> set(starters)
        
    def run(self):
        log("EDGE", "🔫 Starting Prop Edge Run...")
        
        total_found = 0
        
        for league_name, sport_key in self.leagues:
            log("EDGE", f"Analyzing {league_name}...")
            
            # 1. Fetch Odds First
            # Markets: Goal Scorers AND Total Shots (Matching our Model)
            # Corrected Keys based on PDF: player_goal_scorer_anytime, player_shots
            odds_data = fetch_prop_odds(sport_key, markets="player_goal_scorer_anytime,player_shots")
            if not odds_data:
                log("EDGE", f"No odds found for {league_name}. Skipping.")
                continue
                
            # 2. Initialize Model
            predictor = PlayerPropsPredictor(league=league_name, season="2025")
            
            # 3. Iterate through players with odds
            for player_name, markets in odds_data.items():
                
                # --- MARKET 1: ANYTIME GOAL SCORER ---
                if 'player_goal_scorer_anytime' in markets:
                    # New structure: List of offers
                    goal_offers = markets['player_goal_scorer_anytime']
                    if goal_offers and isinstance(goal_offers, list):
                        # Iterate all offers (each book)
                        for offer in goal_offers:
                             if self.process_market(predictor, player_name, offer, "Anytime Goal", league_name, sport_key):
                                total_found += 1

                # --- MARKET 2: TOTAL SHOTS OVER ---
                # Key changed from player_shots_total_over_under to player_shots
                if 'player_shots' in markets:
                    # List of offers (Over/Under mixed)
                    shot_offers = markets['player_shots']
                    if shot_offers and isinstance(shot_offers, list):
                        for offer in shot_offers:
                            # Filter for 'Over'
                            if offer.get('side') == 'Over':
                                if self.process_market(predictor, player_name, offer, "Total Shots", league_name, sport_key):
                                    total_found += 1

        log("EDGE", f"🎯 Prop Edge Run Complete. Found {total_found} opportunities.")

    def process_market(self, predictor, player_name, market_data, market_type, league_name, sport_key):
        try:
            book_price = market_data['price']
            line = market_data.get('line', 0.5)
            book = market_data['book']
            matchup_str = market_data['matchup']
            commence_time = market_data.get('commence_time')
            
            # 4. Smart Matchup Parsing
            # A. Get Baseline Stats
            base_stats = predictor.get_player_rolling_stats(player_name)
            if not base_stats: return False
                
            hero_team = base_stats['team_name']
            
            # B. Identify Opponent
            from utils import normalize_team_name
            parts = matchup_str.split(' vs ')
            opponent_name = None
            if len(parts) == 2:
                t1, t2 = parts[0], parts[1]
                if normalize_team_name(hero_team) in normalize_team_name(t1):
                    opponent_name = t2
                elif normalize_team_name(hero_team) in normalize_team_name(t2):
                    opponent_name = t1
                    
            # --- STARTING XI CHECK (New) ---
            lineup_bonus = 0.0
            if commence_time:
                try:
                    # Convert ISO to datetime
                    # Format: 2026-01-24T12:00:00Z
                    # Check if game is within 60 mins
                    from datetime import timedelta
                    import pytz
                    
                    # Handle Z format
                    ts_val = commence_time.replace('Z', '+00:00')
                    dt_kickoff = datetime.fromisoformat(ts_val)
                    now_utc = datetime.now(pytz.utc)
                    
                    time_diff = dt_kickoff - now_utc
                    hours_until = time_diff.total_seconds() / 3600.0
                    
                    # FIX: Filter out started games (allow 5-min buffer)
                    if hours_until < -0.1:
                        # log("INFO", f"Skipping {matchup_str} (Started {hours_until:.1f}h ago)")
                        return False
                    
                    # If game is imminent (< 1.5 hours) OR live, check lineups
                    if -2 < hours_until < 1.5:
                         match_key = f"{league_name}_{matchup_str}"
                         
                         if match_key not in self.lineup_cache:
                             # Fetch unique lineup
                             home_raw = parts[0] if len(parts)==2 else "Home"
                             away_raw = parts[1] if len(parts)==2 else "Away"
                             
                             log("PROPS", f"🔎 Checking Lineups for {home_raw} vs {away_raw}...")
                             xi = get_confirmed_lineup(sport_key, home_raw, away_raw)
                             self.lineup_cache[match_key] = xi
                             
                         starters = self.lineup_cache.get(match_key)
                         
                         if starters:
                             # Check if player is starting
                             p_norm = normalize_name(player_name)
                             # Fuzzy-ish check in list
                             is_starting = False
                             for s_name in starters:
                                 if p_norm in s_name or s_name in p_norm:
                                     is_starting = True
                                     break
                                     
                             if is_starting:
                                 # IMPROVEMENT: Step 10 - Lineup Confirmation Bonus
                                 # Confirmed starter = Higher confidence (less sub usage risk, guarantee selection)
                                 lineup_bonus = 0.02 # +2% Probability Check
                                 log("PROPS", f"✅ {player_name} CONFIRMED STARTER. Applying +2% edge bonus.")
                             else:
                                 log("INFO", f"🚫 SKIPPING {player_name}: Not in Starting XI.")
                                 return False
                         else:
                             # CRITICAL FIX: If we expected lineups (imminent game) but got None,
                             # it means we lack the intelligence to verify.
                             # Fail Safe: Do NOT bet blindly on starters.
                             log("INFO", f"🚫 SKIPPING {player_name}: Lineup unavailable/pending for imminent match.")
                             return False
                except Exception as e:
                    # Don't fail pipeline on lineup error
                    # log("WARN", f"Lineup check error: {e}")
                    pass

            # C. Re-Run Model with Matchup Adjustment
            if opponent_name:
                stats = predictor.get_player_rolling_stats(player_name, upcoming_opponent=opponent_name)
            else:
                stats = base_stats

            if stats['avg_mins_l5'] < 45 or stats['sample_matches'] < 5: return False

            # 5. Calculate Edge
            prob_model = 0.0
            
            if market_type == "Anytime Goal":
                prob_model = stats['prob_goal'] / 100.0
                selection_text = f"{player_name} Anytime Goalscorer"
            elif market_type == "Total Shots":
                # Calculate Prob(Shots > line)
                # Use Volume Projection (proj_shots_game) as Lambda
                lambda_shots = stats['proj_shots_game']
                
                def poisson_prob_over(lam, target):
                    target_k = int(target) 
                    cumulative_prob = 0.0
                    for k in range(target_k + 1):
                        cumulative_prob += (math.exp(-lam) * (lam**k)) / math.factorial(k)
                    return max(0.0, min(1.0, 1.0 - cumulative_prob))
                
                prob_model = poisson_prob_over(lambda_shots, line)
                selection_text = f"{player_name} Over {line} Shots"

            # Book Implied Probability
            if book_price > 0:
                dec_price = (book_price / 100) + 1
                prob_book = 100 / (book_price + 100)
            else:
                dec_price = (100 / abs(book_price)) + 1
                prob_book = abs(book_price) / (abs(book_price) + 100)
                
            # Apply Lineup Bonus (if any)
            final_model_prob = prob_model + lineup_bonus
            
            edge = final_model_prob - prob_book
            
            if edge >= self.min_edge:
                # Formatting Logic
                if "Anytime Goal" in market_type:
                     final_market = market_type # Just "Anytime Goal"
                elif "Shots" in market_type:
                     final_market = f"{market_type} o{line}" if line else market_type
                else:
                     final_market = market_type

                self.log_opportunity(
                    sport_key=sport_key,
                    player=player_name,
                    matchup=matchup_str,
                    market=final_market,
                    selection=selection_text,
                    price=dec_price,
                    edge=edge,
                    book=book,
                    model_prob=prob_model * 100,
                    kickoff=commence_time
                )
                return True
            return False
            
        except Exception as e:
            log("ERROR", f"Failed to process market for {player_name} ({market_type}): {e}")
            return False

    def log_opportunity(self, sport_key, player, matchup, market, selection, price, edge, book, model_prob, kickoff=None):
        conn = get_db()
        if not conn: return
        
        try:
            with conn.cursor() as cur:
                # Unique ID: PROP_{Player}_{MarketType}_{Date}
                market_slug = market.replace(" ", "")
                unique_id = f"PROP_{player}_{market_slug}_{datetime.now().strftime('%Y%m%d')}"
                
                cur.execute("""
                    INSERT INTO intelligence_log 
                    (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, book, outcome, user_bet)
                    VALUES 
                    (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING', FALSE)
                    ON CONFLICT (event_id) DO NOTHING
                """, (
                    unique_id, 
                    kickoff if kickoff else datetime.now(),
                    sport_key,
                    matchup,
                    selection,
                    price,
                    model_prob,
                    edge,
                    book
                ))
            
            rows = cur.rowcount
            conn.commit()
            
            if rows > 0:
                log("EDGE", f"Logged: {selection} ({price:.2f}) [Edge: {edge*100:.1f}%]")
            # else:
            #     log("DEBUG", f"Skipped duplicate: {selection}")
        except Exception as e:
            log("ERROR", f"Failed to log prop: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    sniper = PropSniper()
    sniper.run()
