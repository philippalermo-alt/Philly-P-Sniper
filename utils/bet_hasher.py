import hashlib
import json

def generate_bet_id(bet: dict) -> str:
    """
    Generate a deterministic SHA256 hash for a bet to prevent duplicates.
    Fields used: sport, market, game_id, section, line, book, odds.
    """
    # Normalize fields
    sport = str(bet.get('sport', '')).strip().lower()
    market = str(bet.get('market', '')).strip().lower()
    
    # Game ID or fallback
    game_id = str(bet.get('game_id', ''))
    if not game_id:
        # Fallback to Home+Away+Date
        h = bet.get('home_team', 'H')
        a = bet.get('away_team', 'A')
        d = bet.get('game_date_est', 'D')
        game_id = f"{h}_{a}_{d}"
        
    # Side/Selection
    selection = str(bet.get('selection', '')).strip().lower()
    
    # Line (optional, e.g. for spreads/totals)
    # Using 'point' or 'total' if available in 'raw_props'? 
    # Or parsing selection?
    # Usually passed in the bet dict or embedded in selection string.
    # We'll stick to selection string as it usually contains the line (e.g. "Magic +2.5").
    
    book = str(bet.get('book', '')).strip().lower()
    odds = str(bet.get('odds_decimal', bet.get('price', 0.0)))
    
    # Construct raw string
    raw = f"{sport}|{market}|{game_id}|{selection}|{book}|{odds}"
    
    # Hash
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
