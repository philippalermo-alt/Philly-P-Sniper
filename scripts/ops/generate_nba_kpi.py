import pandas as pd
import json
import os
from datetime import datetime

def generate_kpi():
    """
    Generate Daily KPI for NBA Model V2.
    Reads recommendations.csv and outputs summarized stats.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    recs_path = f"predictions/nba_model_v2/{today}/recommendations.csv"
    output_path = f"analysis/nba_model_v2/live_kpis/{today}.json"
    
    stats = {
        "date": today,
        "count": 0,
        "avg_odds": 0.0,
        "avg_ev": 0.0,
        "coin_count": 0,
        "dog_count": 0,
        "longshot_count": 0
    }
    
    if os.path.exists(recs_path):
        try:
            df = pd.read_csv(recs_path)
            
            if not df.empty:
                # Ensure numeric
                df['Dec_Odds'] = pd.to_numeric(df['Dec_Odds'], errors='coerce')
                df['Edge_Val'] = pd.to_numeric(df['Edge_Val'], errors='coerce')
                
                stats['count'] = len(df)
                stats['avg_odds'] = round(df['Dec_Odds'].mean(), 2)
                stats['avg_ev'] = round(df['Edge_Val'].mean(), 4)
                
                # Buckets
                stats['coin_count'] = len(df[df['Dec_Odds'] <= 2.0])
                stats['dog_count'] = len(df[(df['Dec_Odds'] > 2.0) & (df['Dec_Odds'] <= 3.0)])
                stats['longshot_count'] = len(df[df['Dec_Odds'] > 3.0])
                
        except Exception as e:
            print(f"Error reading CSV: {e}")
            stats['error'] = str(e)
            
    else:
        stats['status'] = "No Recommendations Found"

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(stats, f, indent=4)
        
    print(f"✅ Generated KPI for {today}: {stats['count']} bets.")

if __name__ == "__main__":
    generate_kpi()
