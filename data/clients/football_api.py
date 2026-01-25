import requests
from datetime import datetime, timedelta
from config.settings import Config
from utils.logging import log

# Will be moved later, but validating import works
# from models.soccer import SoccerModelV2 # Anticipating move

def get_soccer_predictions(league_key):
    """
    Fetch soccer match predictions from Football API.

    Args:
        league_key: Soccer league identifier

    Returns:
        dict: Predictions keyed by matchup string (Away @ Home)
    """
    lid = Config.SOCCER_LEAGUE_IDS.get(league_key)
    if not lid:
        return {}

    preds = {}

    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        for season in [2025, 2024]:
            for date in [today, tomorrow]:
                url = f"https://v3.football.api-sports.io/fixtures?league={lid}&season={season}&date={date}"
                headers = {'x-apisports-key': Config.FOOTBALL_API_KEY}

                try:
                    res = requests.get(url, headers=headers, timeout=10).json()
                    if res.get('results', 0) == 0:
                        continue

                    for f in res.get('response', []):
                        mk = f"{f['teams']['away']['name']} @ {f['teams']['home']['name']}"
                        if mk in preds:
                            continue

                        # --- PHILLY EDGE V2 MODEL ---
                        if 'soccer_model' not in locals():
                            # Dynamic import for now until models are settled
                            try:
                                from models.soccer import SoccerModelV2
                                soccer_model = SoccerModelV2()
                            except ImportError:
                                # Fallback to root (pre-migration) if needed? No, we are restructuring.
                                try:
                                    from soccer_model_v2 import SoccerModelV2
                                    soccer_model = SoccerModelV2()
                                except:
                                    soccer_model = None
                        
                        if soccer_model:
                             pred_res = soccer_model.predict_match(f['teams']['home']['name'], f['teams']['away']['name'])
                             if pred_res:
                                 # Extract Probabilities safely
                                 p_home = pred_res.get('prob_home', 0.0)
                                 p_draw = pred_res.get('prob_draw', 0.0)
                                 p_away = pred_res.get('prob_away', 0.0)
                                 p_over = pred_res.get('prob_over', 0.0) 
                                 
                                 # Extract Expected Score 
                                 try:
                                     parts = pred_res['exp_score'].split(' - ')
                                     hg = float(parts[0])
                                     ag = float(parts[1])
                                 except:
                                     hg, ag = 1.35, 1.35 
                                     
                                 preds[mk] = {
                                     'home_win': p_home,
                                     'draw': p_draw,
                                     'away_win': p_away,
                                     'prob_over': p_over,
                                     'home_goals': hg,
                                     'away_goals': ag,
                                     'home_xg_avg': 0.0,
                                     'away_xg_avg': 0.0,
                                     'home_xga_avg': 0.0,
                                     'away_xga_avg': 0.0
                                 }
                                 continue
                        
                        # Fallback to API
                        p_res = requests.get(
                            f"https://v3.football.api-sports.io/predictions?fixture={f['fixture']['id']}",
                            headers=headers,
                            timeout=10
                        ).json()


                        if p_res.get('results', 0) > 0:
                            pred_data = p_res['response'][0]['predictions']
                            p = pred_data['percent']
                            goals = pred_data.get('goals', {})
                            
                            h_goals = abs(float(goals.get('home', 0))) if goals.get('home') else 1.2
                            a_goals = abs(float(goals.get('away', 0))) if goals.get('away') else 1.0
                            
                            preds[mk] = {
                                'home_win': float(p['home'].strip('%')) / 100,
                                'draw': float(p['draw'].strip('%')) / 100,
                                'away_win': float(p['away'].strip('%')) / 100,
                                'home_goals': h_goals,
                                'away_goals': a_goals,
                                'home_xg_avg': 0.0, 
                                'away_xg_avg': 0.0,
                                'home_xga_avg': 0.0, 
                                'away_xga_avg': 0.0
                            }

                except Exception as e:
                    log("WARN", f"Error in specific fixture for {league_key}: {e}")
                    continue

            if preds:
                break

    except Exception as e:
        log("ERROR", f"Soccer prediction fetch failed: {e}")
        pass

    return preds
