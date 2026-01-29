
import requests
import pandas as pd
import time

def verify_sample():
    print("🧪 Verifying API Sample (PHI 2025)...")
    
    url = (
        "https://api.nhle.com/stats/rest/en/skater/summary?"
        "isAggregate=false&isGame=true&"
        "sort=[{%22property%22:%22gameDate%22,%22direction%22:%22DESC%22}]&"
        "start=0&limit=10&"
        "cayenneExp=seasonId=20252026%20and%20gameTypeId=2%20and%20teamAbbrev=\"PHI\""
    )
    
    try:
        res = requests.get(url, timeout=10)
        print(f"Status Code: {res.status_code}")
        
        if res.status_code == 429:
            print("❌ Still Rate Limited (429).")
            return
            
        data = res.json()
        if 'data' not in data:
            print("❌ No 'data' key.")
            return

        rows = data['data']
        print(f"✅ Received {len(rows)} rows.")
        
        if len(rows) > 0:
            df = pd.DataFrame(rows)
            # Check Critical Fields
            reqs = ['skaterFullName', 'gameDate', 'goals', 'assists', 'points', 'timeOnIcePerGame', 'shots']
            missing = [r for r in reqs if r not in df.columns]
            
            if missing:
                print(f"❌ Missing Fields: {missing}")
            else:
                print("✅ All Critical Fields Present.")
                print(df[reqs].head())
                
                # Check TOI value
                toi = df['timeOnIcePerGame'].iloc[0]
                print(f"Sample TOI: {toi} (Type: {type(toi)})")
                
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    verify_sample()
