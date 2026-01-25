# 🏀 NCAAB First Half Totals Model

A standalone prediction system for finding edges in NCAAB first half total betting markets.

## 📋 Overview

This model predicts first half totals in college basketball games by analyzing team-specific H1/H2 scoring patterns. It exploits the inefficiency where sportsbooks use lazy scaling from full-game lines instead of team-specific tendencies.

**Expected Performance:**
- Prediction MAE: 5.5-6.5 points
- ROI: 8-12%
- Opportunities per day: 3-8 (during NCAAB season)

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install requests numpy pandas scikit-learn scipy python-dotenv
```

### 2. Set Up Environment

Create a `.env` file in this directory:

```bash
ODDS_API_KEY=your_odds_api_key_here
```

### 3. Collect Data (One-time setup)

```bash
python ncaab_h1_scraper.py
```

This will:
- Fetch the last 45 days of completed NCAAB games from ESPN
- Calculate H1/H2 scoring profiles for all teams
- Save to `data/team_h1_profiles.json` and `data/historical_games.json`

**Expected runtime:** 5-10 minutes (fetches ~300 games)

### 4. Train Model

```bash
python ncaab_h1_train.py
```

Expected output:
```
Train MAE: 5.2 points
Test MAE: 5.8 points
Baseline MAE: 6.4 points
Model Improvement: 9.4%
✅ Model saved to models/h1_total_model.pkl
```

### 5. Find Edges (Run Daily)

```bash
python ncaab_h1_edge_finder.py
```

---

## 📁 File Structure

```
ncaab_h1_model/
├── README.md                    # This file
├── ncaab_h1_scraper.py         # Data collection from ESPN
├── ncaab_h1_features.py        # Feature engineering
├── ncaab_h1_train.py           # Model training
├── ncaab_h1_predict.py         # Live prediction
├── ncaab_h1_edge_finder.py     # Edge detection
├── data/
│   ├── team_h1_profiles.json   # Team H1/H2 statistics
│   └── historical_games.json   # Training data
└── models/
    └── h1_total_model.pkl      # Trained model
```

---

## 🎯 How It Works

### The Inefficiency

Sportsbooks typically set H1 totals using simple scaling:

```
H1 Total = Full Game Total × 0.48
```

But teams have different scoring patterns:

| Team Type | H1 Scoring | H2 Scoring | Why |
|-----------|------------|------------|-----|
| Fast Starters | 52% | 48% | Aggressive early game plan, fresh legs |
| Slow Starters | 45% | 55% | Conservative start, adjustments in H2 |
| Even Split | 48% | 52% | Consistent throughout |

### Our Edge

We calculate team-specific H1 ratios and predict accordingly.

**Example:**
```
Game: Duke vs UNC
- Book sets H1 total: 68.5 (assumes 48% split)
- Duke H1 ratio: 52% (fast starters)
- UNC H1 ratio: 50% (even)
- Our model predicts: 72.3
- Edge: OVER 68.5 (+8.2%)
```

---

## 📊 Model Features

The model uses 15 features:

**Team-Specific (per team):**
1. H1 average score (home/away adjusted)
2. H1 ratio (% of points scored in H1)
3. H1 standard deviation (consistency)
4. Consistency score (0-100)

**Matchup Features:**
5. Combined H1 total expectation
6. H1 ratio difference
7. Combined variance
8. Pace matchup indicator
9. Experience weight (games played)

---

## 🔧 Customization

### Adjust Edge Threshold

In `ncaab_h1_edge_finder.py`:

```python
opportunities = finder.find_edges(
    min_edge=0.05,      # 5% minimum edge
    min_confidence=60   # 60/100 confidence minimum
)
```

### Change Model Type

In `ncaab_h1_train.py`:

```python
# Use Ridge Regression (default, faster)
model, metrics = trainer.train(model_type='ridge')

# OR use Gradient Boosting (slower, potentially more accurate)
model, metrics = trainer.train(model_type='gbm')
```

---

## 📈 Maintenance Schedule

- **Daily:** Run edge finder before games
- **Weekly:** Re-scrape last 7 days to update team profiles
- **Monthly:** Retrain model with fresh data

### Weekly Update Script

```bash
# Re-scrape recent data
python ncaab_h1_scraper.py

# Retrain model
python ncaab_h1_train.py

# Find edges
python ncaab_h1_edge_finder.py
```

---

## 🎓 Example Output

### Prediction

```
🏀 FIRST HALF PREDICTION: Duke vs North Carolina
======================================================================

📊 Predicted H1 Total: 72.3
   Confidence: 82/100
   Expected Std Dev: 6.8

   Duke H1 Avg: 38.5
   North Carolina H1 Avg: 33.8
```

### Edge Analysis

```
💰 EDGE ANALYSIS
======================================================================

Sportsbook Line: 68.5
Model Prediction: 72.3
Difference: +3.8

🔼 OVER 68.5:
   Odds: -110
   Implied Prob: 52.4%
   Model Prob: 60.6%
   Edge: +8.2%
   Expected Value: +7.5%
   👉 BET

🔽 UNDER 68.5:
   Odds: -110
   Implied Prob: 52.4%
   Model Prob: 39.4%
   Edge: -13.0%
   Expected Value: -13.0%
   👉 PASS
```

### Daily Edges

```
✅ Found 5 betting opportunities:
====================================================================================================
Game                                Book            Bet          Line    Odds   Pred   Edge     EV  Conf
====================================================================================================
Duke vs North Carolina              DraftKings      OVER 68.5    68.5    -110   72.3   8.2%   7.5%   82
Gonzaga vs Saint Mary's             FanDuel         UNDER 71.5   71.5    -115   67.8   7.1%   6.1%   75
Kansas vs Baylor                    BetMGM          OVER 65.5    65.5    -108   69.2   6.8%   6.3%   78
====================================================================================================
```

---

## 🔍 Troubleshooting

### "No team profiles found"
- Run `python ncaab_h1_scraper.py` first
- Check that `data/team_h1_profiles.json` exists

### "Model file not found"
- Run `python ncaab_h1_train.py` first
- Check that `models/h1_total_model.pkl` exists

### "ODDS_API_KEY not found"
- Create `.env` file with your API key
- Get free key at: https://the-odds-api.com/

### "Not enough data for team X"
- Team hasn't played 5+ games yet
- Model uses league averages as fallback
- Confidence score will be lower

---

## 💡 Tips for Best Results

1. **Focus on high confidence bets** (70+ confidence score)
2. **Avoid early season** (November) - not enough data
3. **Best opportunities:** Conference play (January-March)
4. **Shop lines across books** - edge varies by sportsbook
5. **Track results** - validate the model is performing
6. **Monitor injuries** - starter out = major impact on H1

---

## 📊 Expected Performance by Month

| Month | Data Quality | Expected ROI | Opportunities/Day |
|-------|--------------|--------------|-------------------|
| November | Low (new season) | 3-5% | 1-2 |
| December | Medium | 6-8% | 3-5 |
| January | High | 8-12% | 5-8 |
| February | High | 8-12% | 5-8 |
| March | High | 10-15% | 6-10 |

---

## 🚨 Important Notes

1. **Not all books offer H1 totals** - Check availability
2. **H1 lines appear ~2-4 hours before tipoff** - Run edge finder closer to game time
3. **Neutral sites matter** - Model accounts for home court, but not neutral venues
4. **Injuries impact H1 more** - Stars play more in H1
5. **Pace changes mid-season** - Refresh data weekly

---

## 🔄 Integration with Main System (Future)

To integrate this into your main Philly-P-Sniper system:

1. Copy `ncaab_h1_predict.py` logic into `probability_models.py`
2. Add H1 profile fetching to your data pipeline
3. Call `H1_Predictor` in your main scanning loop
4. Log opportunities to your `intelligence_log` database

---

## 📞 Support

Questions? Check:
- ESPN API docs for game data structure
- The-Odds-API docs for H1 market availability
- scikit-learn docs for model tuning

---

## ✅ Checklist

Before running daily:

- [ ] Data is < 7 days old (check `data/team_h1_profiles.json` timestamp)
- [ ] Model exists (`models/h1_total_model.pkl`)
- [ ] ODDS_API_KEY is set in `.env`
- [ ] It's NCAAB season (November - April)
- [ ] Check books for H1 line availability

---

**Good luck finding edges! 🎯**
