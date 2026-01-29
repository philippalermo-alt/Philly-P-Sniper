import pandas as pd
import os

FILES = {
    "odds": "Hockey Data/nhl_totals_odds_close.csv",
    "moneypuck": "Hockey Data/Game level data.csv",
    "nhl_ref": "nhl_ref_game_logs_v2.csv"
}

def get_unique_teams(filepath, team_columns):
    try:
        # Debug: Sample only
        df = pd.read_csv(filepath, nrows=1000)
        teams = set()
        for col in team_columns:
            if col in df.columns:
                teams.update(df[col].unique().astype(str))
        return sorted(list(teams))
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def main():
    print("Analyze Team Names...")
    
    odds_teams = get_unique_teams(FILES["odds"], ["home_team", "away_team"])
    moneypuck_teams = get_unique_teams(FILES["moneypuck"], ["team", "opposingTeam"]) # MoneyPuck uses 'team' (and 'opposingTeam')
    # Remove redundant call that might fail if columns don't exist
    # nhl_ref_teams = get_unique_teams(FILES["nhl_ref"], ["Home", "Visitor"]) 
    
    # 3. Reference Data (Game column: "Chicago Blackhawks at Florida Panthers")
    try:
        df_ref = pd.read_csv(FILES["nhl_ref"], nrows=1000)
        ref_teams = set()
        if 'Game' in df_ref.columns:
            for game_str in df_ref['Game'].dropna():
                if " at " in game_str:
                    parts = game_str.split(" at ")
                    if len(parts) == 2:
                        ref_teams.add(parts[0].strip())
                        ref_teams.add(parts[1].strip())
        nhl_ref_teams = sorted(list(ref_teams))
    except Exception as e:
        nhl_ref_teams = [f"Error: {e}"]

    # Write to file
    with open("analysis/nhl_team_names.txt", "w") as f:
        f.write("--- Unique Teams ---\n\n")
        f.write(f"Odds API ({len(odds_teams)}): {odds_teams}\n\n")
        f.write(f"MoneyPuck ({len(moneypuck_teams)}): {moneypuck_teams}\n\n")
        f.write(f"NHL Ref ({len(nhl_ref_teams)}): {nhl_ref_teams}\n\n")
        
        all_teams = set(odds_teams) | set(moneypuck_teams) | set([t for t in nhl_ref_teams if not t.startswith("Error")])
        f.write(f"Total Unique Team Strings: {len(all_teams)}\n")
        f.write(str(sorted(list(all_teams))))
    
    print("Analysis written to analysis/nhl_team_names.txt")

