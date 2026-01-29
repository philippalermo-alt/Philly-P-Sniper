import pandas as pd
df = pd.read_csv("Hockey Data/nhl_totals_features_v1.csv")
df['date'] = pd.to_datetime(df['date'])
odds_era = df[df['date'] >= '2022-10-01']

print(f"Odds Era Rows: {len(odds_era)}")
print("NaN Counts (Odds Era):")
print(odds_era.isna().sum().sort_values(ascending=False).head(10))

# Check Shift(1) logic manually for one team
# Sort by date
sample = df[df['team_norm_home'] == 'BOS'].sort_values('date').head(12)
print("\nSample Shift Check (BOS):")
print(sample[['date', 'goalsFor_home', 'rolling_goals_L10_home']])
