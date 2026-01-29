import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..')) # Add project root
from scripts.clean_room.normalize_teams import normalize_team

FILES = {
    "odds": "Hockey Data/nhl_totals_odds_close.csv",
    "nhl_ref": "nhl_ref_game_logs_v2.csv",
    "moneypuck": "Hockey Data/Game level data.csv"
}

def audit_join():
    print("Loading datasets...")
    df_odds = pd.read_csv(FILES["odds"])
    df_ref = pd.read_csv(FILES["nhl_ref"])
    
    # 1. Normalize Odds
    df_odds['home_norm'] = df_odds['home_team'].apply(normalize_team)
    df_odds['away_norm'] = df_odds['away_team'].apply(normalize_team)
    df_odds['date_norm'] = pd.to_datetime(df_odds['game_date']).dt.strftime('%Y-%m-%d')
    
    # 2. Normalize Ref
    # Ref has "Game" column "Team A at Team B" -> Away at Home
    def parse_ref_game(row):
        g = row['Game']
        if " at " in g:
            parts = g.split(" at ")
            return parts[1], parts[0] # Home, Away
        return None, None

    # Apply parse
    df_ref[['home_raw', 'away_raw']] = df_ref.apply(parse_ref_game, axis=1, result_type='expand')
    df_ref['home_norm'] = df_ref['home_raw'].apply(normalize_team)
    df_ref['away_norm'] = df_ref['away_raw'].apply(normalize_team)
    df_ref['date_norm'] = pd.to_datetime(df_ref['Date']).dt.strftime('%Y-%m-%d')
    
    # 3. Join
    print("Performing Odds -> Ref Join...")
    # Join on Date, Home, Away
    merged = pd.merge(
        df_odds,
        df_ref,
        left_on=['date_norm', 'home_norm', 'away_norm'],
        right_on=['date_norm', 'home_norm', 'away_norm'],
        how='left',
        indicator=True
    )
    
    # 3b. Load and Normalize MoneyPuck
    print("Performing Odds -> MoneyPuck Join...")
    try:
        df_mp = pd.read_csv(FILES["moneypuck"])
        # MoneyPuck has 'gameDate' as 20221007 (int) or 2022-10-07?
        # Check step 13922: format string length 8 -> YYYYMMDD
        df_mp['date_str'] = df_mp['gameDate'].astype(str)
        df_mp['date_norm'] = df_mp['date_str'].apply(lambda x: f"{x[:4]}-{x[4:6]}-{x[6:]}" if len(x)==8 else x)
        
        # MoneyPuck teams are in 'team' and 'opposingTeam'
        # We need to match Odds(Home) = MP(Team) & Odds(Away) = MP(Opposing) OR Vice Versa
        # MoneyPuck defines row per team. So we filter for home team rows?
        # Usually MoneyPuck has 'home_or_away' column.
        if 'home_or_away' in df_mp.columns:
            df_mp_home = df_mp[df_mp['home_or_away'] == 'HOME'].copy()
            df_mp_home['home_norm'] = df_mp_home['team'].apply(normalize_team)
            df_mp_home['away_norm'] = df_mp_home['opposingTeam'].apply(normalize_team)
            
            # Join Odds -> MP
            merged_mp = pd.merge(
                df_odds,
                df_mp_home,
                left_on=['date_norm', 'home_norm', 'away_norm'],
                right_on=['date_norm', 'home_norm', 'away_norm'],
                how='left',
                indicator=True
            )
            mp_match_rate = merged_mp['_merge'].value_counts(normalize=True).get('both', 0)
            mp_unmatched = merged_mp[merged_mp['_merge'] == 'left_only']
        else:
            mp_match_rate = 0
            mp_unmatched = pd.DataFrame()

    except Exception as e:
        print(f"Error processing MoneyPuck: {e}")
        mp_match_rate = 0
        mp_unmatched = pd.DataFrame()

    match_rate_ref = merged['_merge'].value_counts(normalize=True).get('both', 0)

    # 4. Generate Report Content
    report = f"""
# Phase 2 Join Audit (Step 2)

## 1. Odds <-> NHL Reference Join
- **Status**: {match_rate_ref:.1%} Match
- **Note**: Low match rate expected as Ref Logs coverage is partial (2025-26 only).

## 2. Odds <-> MoneyPuck Join (PRIMARY)
- **Status**: {mp_match_rate:.1%} Match
- **Total Odds Records**: {len(df_odds)}
- **Matched MoneyPuck**: {len(merged_mp[merged_mp['_merge'] == 'both']) if 'merged_mp' in locals() else 0}

### MoneyPuck Unmatched Analysis
Count: {len(mp_unmatched)}
Sample Unmatched:
{mp_unmatched[['game_date', 'home_team', 'away_team']].head().to_string() if not mp_unmatched.empty else "None"}

## Conclusion
Join integrity with MoneyPuck is {"STRONG" if mp_match_rate > 0.95 else "WEAK"}.
"""
    
    with open("analysis/nhl_phase2_totals/totals_phase2_data_audit.md", "w") as f:
        f.write(report)
    print("Audit written to analysis/nhl_phase2_totals/totals_phase2_data_audit.md")

if __name__ == "__main__":
    audit_join()
