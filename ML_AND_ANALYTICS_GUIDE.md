# Machine Learning & Analytics Guide

## Overview

Your betting system now includes advanced machine learning models, closing line value (CLV) tracking, and comprehensive backtesting capabilities to improve performance and measure edge.

## New Features

### 1. Closing Line Value (CLV) Tracking ✅

**What is CLV?**
Closing Line Value measures how much you beat the market by comparing your bet odds to the closing line (final odds before the game starts). Consistently positive CLV is the #1 indicator of long-term profitability.

**How it works:**
- System automatically fetches closing odds 2 hours before game time
- Calculates CLV: `(your_odds - closing_odds) / your_odds * 100`
- Positive CLV = you got better odds than the sharp money
- Tracks CLV performance over time

**Implementation:**
```python
from closing_line import fetch_closing_odds, get_clv_stats

# Automatically called in hard_rock_model.py
fetch_closing_odds()

# Get CLV statistics
stats = get_clv_stats(sport='NBA', days=30)
print(f"Average CLV: {stats['avg_clv']}%")
print(f"Positive CLV Rate: {stats['positive_clv_pct']}%")
```

**Database schema:**
The `closing_odds` column is now properly populated (was previously broken - it was just copying the opening odds).

### 2. Historical Performance Backtesting ✅

**What is backtesting?**
Analyzes past bets to evaluate model accuracy, identify profitable patterns, and find areas for improvement.

**Metrics analyzed:**
- **Overall Performance**: Win rate, ROI, total profit
- **Calibration**: Are predicted probabilities accurate?
- **Edge Analysis**: Performance by edge size buckets
- **Sport Breakdown**: Which sports are most profitable?
- **Sharp Score Analysis**: Does sharp money correlation matter?
- **CLV Analysis**: ROI for positive vs negative CLV bets
- **Time Series**: Cumulative profit, drawdowns, streaks

**Run a backtest:**
```bash
# Last 30 days (default)
python run_backtest.py

# Custom timeframe
python run_backtest.py 90  # Last 90 days
```

**Programmatic usage:**
```python
from backtesting import run_backtest, print_backtest_report
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=60)

results = run_backtest(start_date, end_date, sport='NBA')
print_backtest_report(results)
```

**Output includes:**
- Overall win rate and ROI
- Expected vs actual ROI (model calibration)
- Sharpe ratio (risk-adjusted returns)
- Max win/loss streaks
- Performance by edge buckets (0-3%, 3-6%, etc.)
- Performance by sport
- CLV analysis
- Calibration curves (predicted vs actual win rates)

### 3. Machine Learning Models 🤖

**What do ML models do?**
Learn from historical data to predict bet outcomes more accurately than pure statistical models.

**Models included:**
1. **Random Forest**: Ensemble of decision trees
2. **Gradient Boosting**: Sequential tree optimization
3. **Logistic Regression**: Linear probability model
4. **Ensemble**: Averages all three for best performance

**Features used:**
- Opening odds and true probability
- Edge value
- Sharp score
- Public betting percentages (ticket % vs money %)
- CLV (for training data)
- Sharp indicator (money % - ticket %)
- Market type (ML, spread, total)
- Betting line
- Sport type

**Train a model:**
```bash
python train_ml_model.py
```

This will:
- Load last 90 days of settled bets
- Train Random Forest, Gradient Boosting, and Logistic Regression
- Evaluate performance on test set
- Save model to `models/betting_model.pkl`
- Print feature importances

**Programmatic usage:**
```python
from ml_models import BettingMLModel, train_and_save_model

# Train new model
model = train_and_save_model(sport='NBA', days_back=90)

# Load existing model
model = BettingMLModel.load('models/betting_model.pkl')

# Predict probability
features = {
    'odds': 2.0,
    'edge': 0.05,
    'true_prob': 0.55,
    'sharp_score': 75,
    'ticket_pct': 35,
    'money_pct': 60,
    # ... other features
}

win_prob = model.predict_proba(features)
print(f"ML predicted win probability: {win_prob:.2%}")
```

**Model performance:**
- Accuracy: Percentage of correct predictions
- AUC: Area Under ROC Curve (0.5 = random, 1.0 = perfect)
- Log Loss: Calibration metric (lower is better)

**Feature importance:**
The training script shows which features matter most for predictions, helping you understand what drives profitable bets.

### 4. Integration with Main System

**Automatic CLV tracking:**
Every time `hard_rock_model.py` runs, it:
1. Settles completed bets
2. **Fetches closing odds for upcoming bets (NEW)**
3. Continues with normal operations

**Optional ML integration:**
To use ML predictions in your recommendation engine (future enhancement):
```python
from ml_models import load_or_train_model

model = load_or_train_model()
if model.is_trained:
    ml_prob = model.predict_proba(features)
    # Blend with statistical probability
    final_prob = 0.7 * true_prob + 0.3 * ml_prob
```

## Module Structure

```
New Modules:
├── closing_line.py         # CLV tracking
├── backtesting.py          # Historical analysis
├── ml_features.py          # Feature engineering
├── ml_models.py            # ML training/prediction
├── train_ml_model.py       # Training script
└── run_backtest.py         # Backtest script
```

## Workflow

### Daily Operation
```bash
# Run as usual (now includes CLV tracking)
python hard_rock_model.py
```

### Weekly Analysis
```bash
# Run backtest to evaluate performance
python run_backtest.py 7

# Review results
# Identify profitable patterns
# Adjust strategy if needed
```

### Monthly Model Updates
```bash
# Retrain ML model with new data
python train_ml_model.py

# This learns from recent bets
# Adapts to changing market conditions
```

## Understanding the Metrics

### Closing Line Value (CLV)
- **Positive CLV**: You beat the market, got better odds
- **Negative CLV**: Line moved against you
- **Target**: 55%+ positive CLV rate
- **Elite**: Average CLV > 2%

### Return on Investment (ROI)
- **Breakeven**: -4.5% to 0% (accounting for vig)
- **Good**: 2-5%
- **Excellent**: 5-10%
- **Suspicious**: >10% (small sample or lucky variance)

### Sharpe Ratio
- **< 0**: Losing money
- **0-1**: Barely profitable
- **1-2**: Good risk-adjusted returns
- **> 2**: Excellent risk-adjusted returns

### AUC (ML Model)
- **0.50**: No better than coin flip
- **0.55-0.60**: Weak edge
- **0.60-0.65**: Moderate edge
- **> 0.65**: Strong predictive power

## Best Practices

### 1. CLV is King
- Focus on bets with positive CLV
- If you're consistently negative CLV, you're betting too late
- Target line shopping and early betting

### 2. Sample Size Matters
- Need 100+ bets for meaningful statistics
- Don't panic over small samples
- Focus on long-term trends

### 3. Calibration Check
- Run monthly backtests
- Check if predicted probabilities match actual outcomes
- Adjust model if miscalibrated

### 4. ML Model Maintenance
- Retrain every 30 days minimum
- Markets evolve, models must adapt
- Monitor performance metrics

### 5. Sport-Specific Analysis
- Different sports have different edges
- Focus capital on your most profitable sports
- Some sports may be unprofitable - avoid them

## Troubleshooting

### No CLV data showing?
- Need to wait 2 hours before game time for closing odds
- Check that `fetch_closing_odds()` is running
- Verify API key is valid

### Backtest showing no data?
- Need settled bets (WON/LOST, not PENDING)
- Check date range includes completed games
- Verify database connection

### ML training fails?
- Need at least 50 settled bets for training
- Check scikit-learn is installed: `pip install scikit-learn`
- Verify database has sufficient data

### Poor ML performance?
- May need more training data (90+ days)
- Try different model types
- Check feature engineering
- Ensure data quality

## Next Steps

1. **Monitor CLV**: After a week, check your CLV stats
2. **Run First Backtest**: After 2 weeks, run comprehensive backtest
3. **Train ML Model**: After 30 days, train your first ML model
4. **Optimize Strategy**: Use insights to refine betting approach

## Advanced Usage

### Custom Backtests
```python
from backtesting import run_backtest

# Analyze high-edge bets only
results = run_backtest(min_edge=0.05)

# Analyze specific sport
results = run_backtest(sport='NBA')

# Custom date range
results = run_backtest(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31)
)
```

### Feature Engineering
```python
from ml_features import extract_features_for_match

features = extract_features_for_match(
    home='Lakers',
    away='Warriors',
    sport='NBA',
    ratings=ratings_dict,
    market_type='spread',
    line=-5.5
)
```

### Cross-Validation
```python
from ml_models import BettingMLModel
from ml_features import prepare_training_data

model = BettingMLModel()
X, y, feature_names = prepare_training_data(days=90)

# 5-fold cross-validation
cv_results = model.cross_validate(X, y, cv=5)
```

## Files Generated

- `models/betting_model.pkl` - Trained ML model
- `backtest_results_*.json` - Backtest results (timestamped)

## Dependencies Added

- `scikit-learn` - Machine learning library

Install with:
```bash
pip install -r requirements.txt
```

## Summary

Your system now has professional-grade analytics:
- ✅ **CLV Tracking**: Measure market edge
- ✅ **Backtesting**: Evaluate historical performance
- ✅ **ML Models**: Learn from data to improve predictions
- ✅ **Comprehensive Metrics**: Understand what works

These tools will help you:
1. Identify profitable patterns
2. Avoid unprofitable bets
3. Optimize bankroll allocation
4. Track long-term edge
5. Make data-driven decisions

Focus on positive CLV and consistent ROI over 100+ bets. The ML models and analytics give you the tools - discipline and patience deliver the profits.
