import re

def analyze_dump():
    try:
        with open("curl_dump.html", "r") as f:
            html = f.read()
            
        # Find all var X = JSON.parse(...)
        matches = re.findall(r"var\s+([a-zA-Z0-9_]+)\s*=\s*JSON\.parse", html)
        
        print(f"Found {len(matches)} JSON variables:")
        for m in matches:
            print(f"- {m}")
            
        # Check specifically for shots or roster
        if "rosterData" in matches or "shotsData" in matches:
            print("\n✅ POTENTIAL PLAYER DATA FOUND!")
        else:
            print("\n❌ No obvious player data variables found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analyze_dump()
