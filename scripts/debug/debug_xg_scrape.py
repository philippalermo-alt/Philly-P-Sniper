
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def scrape_xg():
    print("⚽️ Initializing Selenium for TheAnalyst.com...")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    
    try:
        url = "https://theanalyst.com/competition/premier-league/stats"
        print(f"🌍 Navigating to {url}...")
        driver.get(url)
        
        # Wait for something impactful?
        # Typically these sites have a table. Let's wait for ANY table row.
        time.sleep(5) # Simple wait first
        
        # Capture Title
        print(f"   Title: {driver.title}")
        
        # Search for "Expected Goals" in text
        page_source = driver.page_source
        
        if "Expected Goals" in page_source:
            print("✅ FOUND 'Expected Goals' in page source!")
        else:
            print("❌ 'Expected Goals' NOT found in initial load.")
            
        # Save Source
        with open("analyst_dump.html", "w") as f:
            f.write(page_source)
        print("💾 Saved HTML to analyst_dump.html")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_xg()
