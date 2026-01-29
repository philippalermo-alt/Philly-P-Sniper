import pandas as pd
import numpy as np
from db.connection import get_db
import sys

# Usage: python3 scripts/load_kaggle_csv.py data/team_advanced.csv

def load_csv(filepath):
    print(f"📂 Loading {filepath}...")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return

    # Filter for recent seasons (e.g. 2021+)
    # 'season' column usually represents the End Year (e.g. 2024 for 23-24)
    # Let's import EVERYTHING provided, or filter?
    # User focused on 2024. Let's filter >= 2021 to save DB space if needed.
    # Actually, importing all is safer for history.
    
    print(f"   Shape: {df.shape}")
    print(f"   Seasons: {df['season'].unique()}")

    # Normalize Columns
    # CSV Cols: gameid,date,type,teamid,team,home,away,MIN,OFFRTG,DEFRTG,NETRTG,AST%,AST/TO,AST RATIO,OREB%,DREB%,REB%,TOV%,EFG%,TS%,PACE,PIE,win,season
    
    # We need to PIVOT this. 
    # Current: 1 row per team per game.
    # Target: 1 row per game (Home Cols + Away Cols).
    
    # 1. Identify Home vs Away rows
    # The 'home' column contains the Home Team Name. 'team' is the current row's team.
    # If team == home, this is the Home Row.
    
    df['is_home'] = df['team'] == df['home']
    
    # Separate Home and Away Dataframes
    home_df = df[df['is_home']].copy()
    away_df = df[~df['is_home']].copy()
    
    # Merge on Game ID
    # Note: 'gameid' is the join key.
    
    merged = pd.merge(home_df, away_df, on='gameid', suffixes=('_home', '_away'))
    
    # Now map to DB Columns
    # DB Table: nba_historical_games
    # Columns: game_id, season_id, game_date, home_team_name, away_team_name, ...
    
    conn = get_db()
    cur = conn.cursor()
    
    count = 0 
    
    for idx, row in merged.iterrows():
        try:
            # Stats (Home)
            h_efg = row['EFG%_home']
            h_tov = row['TOV%_home']
            h_orb = row['OREB%_home']
            h_pace = row['PACE_home']
            # valid if not nan
            if pd.isna(h_efg): continue
            
            # Stats (Away)
            a_efg = row['EFG%_away']
            a_tov = row['TOV%_away']
            a_orb = row['OREB%_away']
            
            # Scores (Not explicitly in advanced.csv?? Wait.)
            # The 'team_advanced.csv' preview showed:
            # gameid,date,type,teamid,team,home,away,MIN... 
            # IT DOES NOT SHOW 'PTS' (Points) in the head output!!
            # Wait. OFF_RTG and PACE can imply Points roughly, but we need raw score.
            # Does the CSV have 'PTS'? 
            # I must check the columns again. 
            # If PTS is missing, we can't grade the winner!
            
            # Let's assume for now we might need to look for it or calculate it.
            # OffRtg = (Points / Possessions) * 100
            # Possessions ~= Pace * (MIN / 48)
            # So Points = (OffRtg / 100) * (Pace * (MIN/48)) ?
            # That is an approximation.
            
            # RE-VERIFY COLUMNS BEFORE INSERTING
            pass

        except Exception as e:
            pass

    print("⚠️ HOLD UP: I need to verify if 'PTS' or score columns exist in the CSV.")
    print("   If not, we need to join with another file or use OffRtg derived scores.")
    print("   Columns found:", df.columns.tolist())
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    load_csv(sys.argv[1])
