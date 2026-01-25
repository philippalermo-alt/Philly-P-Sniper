"""
NCAAB H1 Edge Finder
Scans upcoming games and finds H1 total betting edges.
"""

import requests
import json
import sys
import os
from datetime import datetime

# Enable importing from parent directory (for database.py)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import get_db, safe_execute
    from utils import log
except ImportError:
    # Fallback if running from root without package structure
    pass

# Handle sibling imports whether run as script or module
try:
    from .ncaab_h1_predict import H1_Predictor
except ImportError:
    from ncaab_h1_predict import H1_Predictor

class H1_EdgeFinder:
    def __init__(self, odds_api_key):
        """Initialize with Odds API key."""
        self.api_key = odds_api_key
        self.predictor = H1_Predictor()
        self.base_url = "https://api.the-odds-api.com/v4/sports"

    def fetch_upcoming_events(self):
        """Fetch list of upcoming NCAAB event IDs."""
        url = f"{self.base_url}/basketball_ncaab/events"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []

    def fetch_event_odds(self, event_id):
        """Fetch H1 odds for a specific event."""
        url = f"{self.base_url}/basketball_ncaab/events/{event_id}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'totals_h1', # Specific H1 market
            'oddsFormat': 'american'
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            # print(f"Error fetching odds for {event_id}: {response.text}")
            return None
        except:
            return None

    def find_edges(self, min_edge=0.07, min_confidence=75):
        """
        Scan all upcoming games for H1 total edges.

        Args:
            min_edge: Minimum edge threshold (default 7% - conservative to account for model error)
            min_confidence: Minimum confidence score (default 75/100 - requires sufficient data)
        """
        if min_edge < 0.07:
            print(f"\n⚠️ NOTE: Scanning with low edge threshold ({min_edge:.1%}) - recommend 7%+ for production.")

        events = self.fetch_upcoming_events()
        print(f"✓ Found {len(events)} upcoming events. Scanning for H1 lines...")
        
        opportunities = []
        stats = {
            'scanned': 0,
            'no_market': 0,
            'high_volatility': 0,
            'low_confidence': 0,
            'qualified': 0,
            'tempo_clash': 0,
            'small_sample': 0,
            'too_volatile': 0,
            'no_data': 0
        }

        print(f"\n🔍 Scanning for H1 edges (Adaptive Thresholds)...")
        print("=" * 80)

        for i, event in enumerate(events):
            stats['scanned'] += 1
            
            # 1. Fetch ODDS for this specific event
            game = self.fetch_event_odds(event['id'])
            if not game: 
                continue

            home_team = game['home_team']
            away_team = game['away_team']
            
            # Progress indicator for large lists
            if i % 10 == 0: print(f"   Scanning {i}/{len(events)}: {home_team} vs {away_team}...")

            # Get model prediction
            prediction = self.predictor.predict(home_team, away_team, verbose=False)
            
            # --- DYNAMIC THRESHOLD LOGIC ---
            # Instead of skipping, we raise the bar.
            current_req_edge = min_edge
            std = prediction['breakdown']['combined_std']
            conf = prediction['confidence']
            
            # Volatility Penalty
            if std > 13.0:
                current_req_edge += 0.04 # Requires +4% more edge
                stats['high_volatility'] += 1
            elif std > 11.0:
                current_req_edge += 0.02
                
            # Confidence Penalty
            # UPDATED: Enforce strict minimum confidence
            if conf < min_confidence:
                stats['low_confidence'] += 1
                continue
                
            if conf < 50: # (Legacy check, technically redundant if min > 50 but kept for safety)
                current_req_edge += 0.02
            
            # Tempo Clash Penalty (if applicable)
            if prediction['breakdown']['tempo_diff'] > 15.0:
                current_req_edge += 0.02
                stats['tempo_clash'] += 1

            # Small Sample Penalty (if applicable)
            if prediction['breakdown']['min_games_played'] < 8:
                current_req_edge += 0.02
                stats['small_sample'] += 1

            # Absolute Safety Floors (Prevent suicide bets)
            if std > 18.0: 
                stats['too_volatile'] += 1
                continue # Truly random
            if conf < 30: 
                stats['no_data'] += 1
                continue # No data
            
            # --- MARKET SCAN ---
            found_h1_market = False
            
            for bookmaker in game.get('bookmakers', []):
                book_name = bookmaker['title']

                for market in bookmaker.get('markets', []):
                    if market['key'] != 'totals_h1': # basketball_ncaab_h1_totals? 
                        # Use loose check if exact key fails: 'h1' in market['key']
                        continue
                        
                    found_h1_market = True
                    
                    # Safe Parsing
                    outcomes = market.get('outcomes', [])
                    if len(outcomes) != 2: continue

                    over_outcome = next((o for o in outcomes if o['name'] == 'Over'), None)
                    under_outcome = next((o for o in outcomes if o['name'] == 'Under'), None)

                    if not over_outcome or not under_outcome: continue

                    # Prioritize point
                    line = over_outcome.get('point', market.get('point'))
                    if line is None: continue

                    # Calculate Edge
                    edge_analysis = self.predictor.calculate_edge(
                        predicted_total=prediction['predicted_h1_total'],
                        sportsbook_line=line,
                        over_odds=over_outcome['price'],
                        under_odds=under_outcome['price'],
                        expected_std=prediction['expected_std']
                    )
                    
                    # Check against DYNAMIC Threshold
                    for side in ['over', 'under']:
                        if edge_analysis[side]['edge'] >= current_req_edge:
                            # Parse Odds
                            odds_val = over_outcome['price'] if side == 'over' else under_outcome['price']
                            
                            opp = {
                                'game': f"{home_team} vs {away_team}",
                                'home_team': home_team, 'away_team': away_team,
                                'bookmaker': book_name, 'bet_type': side.upper(),
                                'line': line, 'odds': odds_val,
                                'predicted': prediction['predicted_h1_total'],
                                'edge': edge_analysis[side]['edge'],
                                'req_edge': current_req_edge, # Log the bar we cleared
                                'ev': edge_analysis[side]['ev'],
                                'confidence': conf,
                                'volatility': std,
                                'kickoff': game.get('commence_time', '')
                            }
                            opportunities.append(opp)
                            self.log_opportunity(opp)
                            stats['qualified'] += 1
            
            if not found_h1_market:
                stats['no_market'] += 1
                # print(f"   [DEBUG] {home_team}: No H1 markets.")

        # Sort by edge (highest first)
        opportunities.sort(key=lambda x: x['edge'], reverse=True)
        self.stats = stats # Store for summary
        return opportunities

    def print_opportunities(self, opportunities):
        """Pretty print with Summary."""
        print("\n📊 SCAN SUMMARY:")
        print(f"   Games Scanned:   {self.stats.get('scanned', 0)}")
        print(f"   No H1 Market:    {self.stats.get('no_market', 0)}")
        print(f"   High Volatility: {self.stats.get('high_volatility', 0)} (Adjusted Threshold)")
        print(f"   Low Confidence:  {self.stats.get('low_confidence', 0)} (Adjusted Threshold)")
        print(f"   Tempo Clash:     {self.stats.get('tempo_clash', 0)} (Adjusted Threshold)")
        print(f"   Small Sample:    {self.stats.get('small_sample', 0)} (Adjusted Threshold)")
        print(f"   Too Volatile:    {self.stats.get('too_volatile', 0)} (Skipped)")
        print(f"   No Data:         {self.stats.get('no_data', 0)} (Skipped)")
        print(f"   ✅ Qualified:    {self.stats.get('qualified', 0)}")
        
        if not opportunities:
            print("\n❌ No edges meet the dynamic thresholds.")
            return

        print(f"\n✅ Found {len(opportunities)} betting opportunities:")
        print("=" * 110)
        print(f"{'Game':<30} {'Book':<12} {'Bet':<10} {'Line':>5} {'Odds':>5} {'Pred':>5} {'Edge':>6} {'Req%':>5} {'Vol':>4} {'Conf':>4}")
        print("=" * 110)

        for opp in opportunities:
            game_short = opp['game'][:28]
            bet_str = f"{opp['bet_type']} {opp['line']}"

            print(f"{game_short:<30} {opp['bookmaker']:<12} {bet_str:<10} "
                  f"{opp['line']:>5.1f} {opp['odds']:>5} {opp['predicted']:>5.1f} "
                  f"{opp['edge']:>6.1%} {opp['req_edge']:>5.1%} {opp['volatility']:>4.1f} {opp['confidence']:>4.0f}")

        print("=" * 110)

    def log_opportunity(self, opp):
        """Save opportunity to database."""
        conn = get_db()
        if not conn: return
        
        try:
            with conn.cursor() as cur:
                # 1H TOTAL Structure
                sel = f"1H {opp['bet_type'].title()} {opp['line']}"
                event_id = f"NCAAB_H1_{opp['home_team']}_{opp['bet_type']}_{datetime.now().strftime('%Y%m%d')}"
                
                # Check for Conflict (Last Bet Stands)
                # Since this model is simpler, we just overwrite using ON CONFLICT logic below
                # or we could add the swap logic if needed. 
                # For now, standard insert.
                
                sql = """
                    INSERT INTO intelligence_log 
                    (event_id, timestamp, kickoff, sport, teams, selection, odds, true_prob, edge, book, outcome, user_bet, trigger_type)
                    VALUES 
                    (%s, NOW(), %s, 'NCAAB', %s, %s, %s, %s, %s, %s, 'PENDING', FALSE, 'h1_model')
                    ON CONFLICT (event_id) DO UPDATE SET
                        odds=EXCLUDED.odds, edge=EXCLUDED.edge, timestamp=NOW();
                """
                
                # Convert confidence to prob heuristic (0-100 -> 0.0-1.0)
                # Not exact true_prob, but useful for storage
                true_prob = opp['confidence'] / 100.0
                
                # FIX: Convert American Odds to Decimal for DB
                raw_odds = float(opp['odds'])
                if raw_odds > 0:
                    dec_odds = 1 + (raw_odds / 100)
                else:
                    dec_odds = 1 + (100 / abs(raw_odds))
                
                cur.execute(sql, (
                    event_id,
                    opp['kickoff'],
                    opp['game'],
                    sel,
                    float(round(dec_odds, 3)),
                    float(true_prob),
                    float(opp['edge']),
                    opp['bookmaker']
                ))
            conn.commit()
            if 'log' in globals():
                log("H1_MODEL", f"Logged: {opp['game']} - {sel}")
            else:
                print(f"   💾 Saved to DB: {sel}")
                
        except Exception as e:
            print(f"❌ Failed to log to DB: {e}")
        finally:
            conn.close()

    def export_opportunities(self, opportunities, filename='h1_edges.json'):
        """Export opportunities to JSON for logging."""
        with open(filename, 'w') as f:
            json.dump(opportunities, f, indent=2)

        print(f"\n📁 Exported {len(opportunities)} opportunities to {filename}")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv('ODDS_API_KEY')

    if not api_key:
        print("❌ ODDS_API_KEY not found in environment")
        exit(1)

    # Find edges (using conservative thresholds)
    # Find edges (using configurable thresholds)
    # UPDATED: Stricter defaults to prevent leaks (User Request)
    min_edge = float(os.getenv('NCAAB_MIN_EDGE', 0.085))
    min_conf = float(os.getenv('NCAAB_MIN_CONF', 80))
    
    finder = H1_EdgeFinder(api_key)
    
    # Notify user if running loose
    if min_edge < 0.05:
        print(f"🔓 LOOSE SCAN ENABLED: Edge {min_edge:.1%}, Conf {min_conf}")

    opportunities = finder.find_edges(min_edge=min_edge, min_confidence=min_conf)

    # Display
    finder.print_opportunities(opportunities)

    # Export
    if opportunities:
        finder.export_opportunities(opportunities)
