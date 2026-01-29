import pandas as pd

FILE_PATH = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data/Game level data.csv"

def full_scan():
    print(f"🕵️‍♂️ Scanning ENTIRE file: {FILE_PATH}")
    try:
        # Load only 'position' column to save memory if needed, but file isn't that big.
        df = pd.read_csv(FILE_PATH, usecols=['position', 'name'])
        print(f"📊 Total Rows: {len(df)}")
        
        unique_positions = df['position'].unique()
        print(f"📍 All Unique Positions: {unique_positions}")
        
        if 'G' in unique_positions:
            print("✅ FOUND GOALIES in full scan!")
        else:
            print("❌ No Goalies found in entire file.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    full_scan()
