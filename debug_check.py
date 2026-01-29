import requests
import sys

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

def check():
    url = "https://leftwinglock.com/starting-goalies/"
    print(f"Fetching {url}...")
    resp = requests.get(url, cookies=COOKIES, headers=HEADERS)
    html = resp.text
    
    keyword = "Confirmed"
    idx = html.find(keyword)
    if idx != -1:
        print(f"Found '{keyword}' at index {idx}")
        start = max(0, idx - 500)
        end = min(len(html), idx + 500)
        print("CONTEXT:")
        print(html[start:end])
    else:
        print(f"Keyword '{keyword}' not found.")

if __name__ == "__main__":
    check()
