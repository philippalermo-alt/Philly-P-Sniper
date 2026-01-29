import requests
from bs4 import BeautifulSoup
from utils.logging import log
from utils.team_names import normalize_team_name

# LWL Cookies (Provided by User)
COOKIES = {
    "xf_from_search": "google",
    "xf_csrf": "GM9ec00WL0VKNJbz",
    "xf_user": "56044,jMoWtMqXkx-OkZkAsKnNh96I1dHDqjwkA-HfPV2V",
    "xf_session": "fDmJhP7Wt_7N7Lb61Vx5qyPYnN9VPJXJ",
    "xf_siropu_chat_room_id": "1",
    "PHPSESSID": "q3dfej0duu1lh2gfn2ndrpvifk" # User provided this
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://leftwinglock.com/"
}

# LWL Nickname to Full Name Mapping
LWL_TEAM_MAP = {
    "leafs": "toronto maple leafs",
    "predators": "nashville predators",
    "bruins": "boston bruins",
    "sabres": "buffalo sabres",
    "wings": "detroit red wings",
    "kings": "los angeles kings",
    "panthers": "florida panthers",
    "utah": "utah hockey club", # "Utah Mammoth" in some books, handled by global util aliasing?
    "oilers": "edmonton oilers",
    "canucks": "vancouver canucks",
    "kraken": "seattle kraken",
    "ducks": "anaheim ducks",
    "flames": "calgary flames",
    "knights": "vegas golden knights",
    "sharks": "san jose sharks",
    "blackhawks": "chicago blackhawks",
    "blues": "st. louis blues",
    "jets": "winnipeg jets",
    "stars": "dallas stars",
    "wild": "minnesota wild",
    "avalanche": "colorado avalanche",
    "canadiens": "montreal canadiens",
    "senators": "ottawa senators",
    "lightning": "tampa bay lightning",
    "flyers": "philadelphia flyers",
    "capitals": "washington capitals",
    "islanders": "new york islanders",
    "devils": "new jersey devils",
    "rangers": "new york rangers",
    "hurricanes": "carolina hurricanes",
    "jackets": "columbus blue jackets",
    "penguins": "pittsburgh penguins"
}

def fetch_lwl_goalies():
    """
    Scrapes LeftWingLock for starting goalies using session cookies.
    """
    url = "https://leftwinglock.com/starting-goalies/"
    log("GOALIE_SCRAPER", f"Fetching {url} (LWL)...")
    
    try:
        resp = requests.get(url, cookies=COOKIES, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            log("GOALIE_SCRAPER", f"❌ LWL Error: {resp.status_code}")
            return {}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        goalie_data = {}
        
        # Strategy: Find all teams and names separately and zip them
        # Teams found in <div class="comparison__person-team">
        team_els = soup.select('div.comparison__person-team')
        
        # Names found in <h4 class="comparison__person-full-name">
        name_els = soup.select('h4.comparison__person-full-name')

        # Status found in <div class="comparison__person-value">
        # Note: Select ALL values, hopefully distinct from stats?
        # The snippet showed: <div class="comparison__person-wrapper-info"><div class="comparison__person-value ...">Confirmed</div></div>
        # Let's try selecting the wrapper-info's first child value?
        # Or just 'div.comparison__person-value' and see if it picks up stats too?
        # Stats usually are in footer list.
        status_els = soup.select('div.comparison__person-value')
        
        # Filter status_els to only those that contain status keywords? 
        # Or check count.
        # If count matches teams (e.g. 26), we are good.
        
        log("GOALIE_SCRAPER", f"DEBUG: Found {len(team_els)} teams, {len(name_els)} names, {len(status_els)} statuses.")
        
        # They should match in count (2 per game)
        limit = min(len(team_els), len(name_els))
        
        # If statuses don't match limit, we need a fallback strategy or relax the filter index
        # Let's assume they match for now.
        
        for i in range(limit):
            try:
                # Team
                raw_team = team_els[i].get_text(strip=True)
                
                # Name
                name = name_els[i].get_text(" ", strip=True) 
                
                # Status
                status = "Likely" 
                if i < len(status_els):
                    status_text = status_els[i].get_text(strip=True).lower()
                    if "confirmed" in status_text:
                        status = "Confirmed"
                    elif "likely" in status_text:
                        status = "Likely"
                    elif "projected" in status_text:
                        status = "Projected"
                    else:
                        status = "Projected" # Default if text acts weird
                
                # STRICT FILTERING: Only Confirmed
                if status != "Confirmed":
                    # log("GOALIE_SCRAPER", f"Skipping {name} (Status: {status})")
                    continue
                
                # Normalize using Map first
                clean_raw = raw_team.lower().strip()
                if clean_raw in LWL_TEAM_MAP:
                    norm_team = normalize_team_name(LWL_TEAM_MAP[clean_raw])
                else:
                    norm_team = normalize_team_name(raw_team)
                
                if norm_team == "Unknown":
                   continue

                goalie_data[norm_team] = {
                    'starter': name,
                    'status': status,
                    'source': 'LeftWingLock'
                }
                log("GOALIE_SCRAPER", f"Parsed & Confirmed: {norm_team} -> {name}")

            except Exception as ex:
                log("GOALIE_SCRAPER", f"Error parsing index {i}: {ex}")
                continue
                
        log("GOALIE_SCRAPER", f"✅ Parsed {len(goalie_data)} CONFIRMED goalies from LWL.")
        return goalie_data
        
    except Exception as e:
        log("GOALIE_SCRAPER", f"❌ Error: {e}")
        return {}
