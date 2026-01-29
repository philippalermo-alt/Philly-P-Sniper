import os
import pandas as pd
import glob

DATA_ROOT = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data"
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-2026"]
REQUIRED_FILES = ["teams.csv", "skaters.csv", "goalies.csv", "lines.csv"]

# Contract Requirements Checklist
REQUIRED_COLUMNS = {
    "teams.csv": ["team", "xGoalsPercentage", "corsiPercentage", "fenwickPercentage", "penalityMinutesFor"],
    "goalies.csv": ["team", "name", "goals", "xGoals"], # For GSAx
    "skaters.csv": ["team", "name", "iceTime"],
    "lines.csv": ["team", "iceTime"]
}

def audit_season(season_folder):
    print(f"\n--- Auditing Season: {season_folder} ---")
    season_path = os.path.join(DATA_ROOT, season_folder)
    
    if not os.path.exists(season_path):
        print(f"❌ Critical: Folder not found: {season_path}")
        return

    files = os.listdir(season_path)
    
    # file normalization check
    file_map = {}
    for f in files:
        if "skaters" in f and f != "skaters.csv":
            print(f"⚠️  Warning: Found variant file '{f}'. Checking if it should be canonical.")
            file_map["skaters.csv"] = f # Treat as skaters.csv for audit
        elif f in REQUIRED_FILES:
            file_map[f] = f
            
    for req_file in REQUIRED_FILES:
        actual_file = file_map.get(req_file)
        
        if not actual_file:
             print(f"❌ Missing File: {req_file}")
             continue
             
        full_path = os.path.join(season_path, actual_file)
        try:
            df = pd.read_csv(full_path)
            print(f"✅ Loaded {req_file} (mapped to {actual_file}): {len(df)} rows, {len(df.columns)} cols")
            
            # Check Schema
            missing_cols = []
            if req_file in REQUIRED_COLUMNS:
                for col in REQUIRED_COLUMNS[req_file]:
                    if col not in df.columns:
                        missing_cols.append(col)
            
            if missing_cols:
                print(f"   ❌ Missing Critical Columns in {req_file}: {missing_cols}")
            else:
                print(f"   ✨ Schema Valid for Critical Features")
                
            # specific checks
            if req_file == "goalies.csv" and "xGoals" in df.columns and "goals" in df.columns:
                 # Check if GSAx calculable
                 pass
            
        except Exception as e:
            print(f"❌ Error reading {full_path}: {e}")

if __name__ == "__main__":
    print("🏒 Starting NHL Data Audit (Clean-Room Protocol)...")
    for season in SEASONS:
        audit_season(season)
    print("\nAudit Complete.")
