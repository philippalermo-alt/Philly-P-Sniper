import requests
import os
import time

URL = "https://moneypuck.com/moneypuck/playerData/careers/gameByGame/all_teams.csv"
OUTPUT_DIR = "/Users/purdue2k5/Documents/Philly-P-Sniper/Hockey Data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "all_teams.csv")

def download_file():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print(f"⬇️  Starting download from: {URL}")
    print(f"📂 Saving to: {OUTPUT_FILE}")
    
    try:
        start_time = time.time()
        response = requests.get(URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(OUTPUT_FILE, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    # Simple progress indicator every 10MB
                    if downloaded % (10 * 1024 * 1024) < block_size:
                        print(f"   ... {downloaded / (1024*1024):.1f} MB downloaded")
                        
        duration = time.time() - start_time
        print(f"✅ Download Complete! ({downloaded / (1024*1024):.1f} MB) in {duration:.1f}s")
        
    except Exception as e:
        print(f"❌ Error downloading file: {e}")

if __name__ == "__main__":
    download_file()
