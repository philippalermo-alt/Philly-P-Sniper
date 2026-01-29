import requests
import sys

URL = "https://leftwinglock.com/starting-goalies/"
COOKIES = {
    "xf_from_search": "google",
    "xf_csrf": "GM9ec00WL0VKNJbz",
    "xf_user": "56044,jMoWtMqXkx-OkZkAsKnNh96I1dHDqjwkA-HfPV2V",
    "xf_session": "fDmJhP7Wt_7N7Lb61Vx5qyPYnN9VPJXJ",
    "xf_siropu_chat_room_id": "1",
    "PHPSESSID": "q3dfej0duu1lh2gfn2ndrpvifk"
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def probe():
    print(f"Fetching {URL}...")
    try:
        resp = requests.get(URL, cookies=COOKIES, headers=HEADERS, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Successfully fetched page.")
            html = resp.text
            # Dump a snippet to finding goalies
            # Look for common team names or 'Confirmed'
            print("Content Snippet (length):", len(html))
            
            # Simple heuristic to find structure
            # LWL usually has class="gamematchup" or similar
            if "gamematchup" in html:
                print("Found 'gamematchup' class.")
            
            # Dump first 500 characters of a relevant section if found
            if "<body" in html:
                start = html.find("<body")
                print(html[start:start+500])
                
            # Verify if we see names
            # Search for 'Confirmed'
            if "Confirmed" in html:
                print("Found 'Confirmed' status.")
            else:
                print("Did NOT find 'Confirmed' status (maybe no games or structure changed).")
                
            # Save to file for inspection if needed
            with open("lwl_debug.html", "w") as f:
                f.write(html)
        else:
            print("Failed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    probe()
