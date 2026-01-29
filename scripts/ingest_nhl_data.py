import os
import pandas as pd
import glob
import re

# Configuration
DATA_ROOT = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data"
OUTPUT_DIR = "/Users/purdue2k5/Documents/Philly-P-Sniper/data/nhl_processed"
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-2026"]

# File variations map
FILE_MAP = {
    "teams.csv": ["teams.csv"],
    "skaters.csv": ["skaters.csv", "skaters (1).csv", "skaters .csv"],
    "goalies.csv": ["goalies.csv"],
    "lines.csv": ["lines.csv"]
}

def normalize_season_id(folder_name):
    """Converts '2022-23' or '2025-2026' to integer start year (e.g. 2022, 2025)"""
    if "-" in folder_name:
        parts = folder_name.split("-")
        return int(parts[0])
    return int(folder_name)

def ingest_category(category_name, file_variants):
    print(f"\n📦 Ingesting Category: {category_name}...")
    all_seasons_data = []
    
    for season_folder in SEASONS:
        season_path = os.path.join(DATA_ROOT, season_folder)
        if not os.path.exists(season_path):
            print(f"  ⚠️  Skipping missing season folder: {season_folder}")
            continue
            
        # Find the matching file
        found_file = None
        for variant in file_variants:
            possible_path = os.path.join(season_path, variant)
            if os.path.exists(possible_path):
                found_file = possible_path
                break
        
        if not found_file:
            print(f"  ❌ Missing {category_name} in {season_folder}")
            continue
            
        print(f"  ✅ Loading {season_folder} -> {os.path.basename(found_file)}")
        try:
            df = pd.read_csv(found_file)
            
            # Standardization
            # Ensure 'season' column exists and is correct integer year
            start_year = normalize_season_id(season_folder)
            df['season'] = start_year 
            
            # Column Normalization (if needed in future, currently seemingly consistent)
            # if 'iceTime' in df.columns: df.rename(columns={'iceTime': 'icetime'}, inplace=True)
            
            all_seasons_data.append(df)
            
        except Exception as e:
            print(f"  ❌ Error reading {found_file}: {e}")

    if not all_seasons_data:
        print(f"❌ No data found for {category_name}")
        return

    # Concatenate
    combined_df = pd.concat(all_seasons_data, ignore_index=True)
    
    # Save to Parquet
    output_path = os.path.join(OUTPUT_DIR, f"{category_name.replace('.csv', '')}_all.parquet")
    combined_df.to_parquet(output_path, index=False)
    print(f"💾 Saved {len(combined_df)} rows to {output_path}")

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print("🏒 Starting NHL Data Ingestion (Clean-Room Protocol)")
    print(f"   Source: {DATA_ROOT}")
    print(f"   Target: {OUTPUT_DIR}")
    
    for category, variants in FILE_MAP.items():
        ingest_category(category, variants)
        
    print("\n✨ Ingestion Complete.")

if __name__ == "__main__":
    main()
