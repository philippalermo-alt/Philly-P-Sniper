import json
import os
import sys
import pandas as pd
from datetime import datetime

OUTPUT_BASE = "analysis/nhl_phase2_totals/live_kpis"

def generate_kpi():
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = f"{OUTPUT_BASE}/{today}.json"
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    
    # Load recent predictions/recs
    recs_path = f"predictions/nhl_totals_v2/{today}/recommendations.csv"
    
    kpi = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "scans_count": 0, # To implement scanning log parsing
        "eligible_count": 0,
        "predictions_count": 0,
        "recommendations_count": 0,
        "avg_ev_recommended": 0.0,
        "sigma_current": 2.2420, # Static for now unless read from model meta
        "status": "OK"
    }
    
    if os.path.exists(recs_path):
        try:
            df = pd.read_csv(recs_path)
            kpi["recommendations_count"] = len(df)
            if "ev" in df.columns and not df.empty:
                kpi["avg_ev_recommended"] = float(df["ev"].mean())
        except Exception as e:
            kpi["error"] = str(e)
            kpi["status"] = "ERROR"
            
    # Serialize
    with open(output_file, 'w') as f:
        json.dump(kpi, f, indent=2)
        
    print(f"KPI Report Generated: {output_file}")

if __name__ == "__main__":
    generate_kpi()
