import requests
from bs4 import BeautifulSoup

# Cookies provided by the user
cookies = {
    'PHPSESSID': '6ipqu5e8eejus53o2cr4m21cuv',
    'pmpro_visit': '1',
    '__stripe_mid': 'bb0a4f8e-860f-46c4-a746-fdc619aac07323078f',
    '__stripe_sid': '961d0b40-32b9-441b-a549-130c50a499d3b174ea',
    'wordpress_logged_in_76ede415765edb5e6771596370878b0f': 'Purdue2k5|1801053372|K9Y4QVeUGo3x1xmtLsqam9ISkr8XXlPlYhfLBFz0sFe|608e641c302fffee22c11c1ad1b9ab024eb3705a1483ec5066be049df34ced6b',
    'wordpress_res': 'Purdue2k5 134053628f9a34761ab4fb52006ede65797db7be',
    'wfwaf-authcookie-1050095bdac4729d84e83d3a7ae63a49': '6468|subscriber|read|249a973f69129765c435148e037a3bf90b6449480e61a9e7eb650bffda448e26',
    'pvc_visits[0]': '1769603622b1042a1769603696b25a1769603698b1163a1769603724b21a1769603777b22'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def probe_site():
    url = "https://evolving-hockey.com/"
    print(f"🕵️‍♂️ Probing {url} with cookies...")
    
    try:
        response = requests.get(url, cookies=cookies, headers=headers)
        print(f"Response Code: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for logout link to verify auth
        logout_links = soup.find_all('a', string=lambda t: t and "Log Out" in t)
        if logout_links:
            print("✅ LOGGED IN! Found 'Log Out' link.")
        else:
            print("⚠️  Not sure if logged in. Checking for 'Log In' link...")
            login_links = soup.find_all('a', string=lambda t: t and "Log In" in t)
            if login_links:
                print("❌ Found 'Log In' link - Cookies might be invalid or expired.")
            else:
                print("❓ Could not find Log In or Log Out links.")

    except Exception as e:
        print(f"❌ Error during homepage probe: {e}")

    print("\n⬇️  Attempting Direct Download from User-Provided Link:")
    # URL provided by user
    download_url = "https://evolving-hockey.com/stats/game_logs/session/24774fdc96a01df3af52d8187d9ee3d6/download/gglog_download?w="
    
    try:
        print(f"   Target: {download_url}")
        r = requests.get(download_url, cookies=cookies, headers=headers, stream=True)
        print(f"   Status Code: {r.status_code}")
        print(f"   Headers: {r.headers}")
        
        if r.status_code == 200:
            content_type = r.headers.get('Content-Type', '')
            if 'csv' in content_type or 'text' in content_type:
                output_file = "goalie_logs_scraped.csv"
                with open(output_file, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"   ✅ Success! Saved to {output_file}")
                
                # Verify rows
                with open(output_file, 'r') as f:
                    lines = f.readlines()
                    print(f"   📊 Row Count: {len(lines)}")
                    print(f"   📝 Header: {lines[0].strip()}")
            else:
                print(f"   ⚠️  Content-Type is {content_type}, might not be CSV.")
                print(f"   Preview: {r.text[:500]}")
        else:
            print(f"   ❌ Failed to download. Status: {r.status_code}")
            print(f"   Response: {r.text[:500]}")

    except Exception as e:
        print(f"   ❌ Error during download: {e}")

if __name__ == "__main__":
    probe_site()
