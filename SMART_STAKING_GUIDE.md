# Smart Staking System Guide

## Overview

The Smart Staking System analyzes your historical betting performance and automatically adjusts stake recommendations based on what's actually working in your betting strategy.

## The Problem It Solves

Traditional Kelly Criterion staking increases stakes as edge increases. However, this can be problematic when:
- High edge bets are actually losing money (model miscalibration)
- Low edge bets in certain sports/ranges are performing excellently
- Different sports have different levels of predictability

**Example from your data:**
- 10%+ edge bets might be losing money → Should stake LESS
- 3-6% edge bets in NBA might be crushing → Should stake MORE

## How It Works

### 1. Historical Analysis

Every time the model runs, it analyzes the last 60 days of settled bets:
- Groups bets by **Sport** (NBA, NFL, NHL, NCAAB)
- Groups bets by **Edge Range** (0-3%, 3-6%, 6-10%, 10%+)
- Calculates actual ROI for each combination

### 2. Performance-Based Multipliers

Based on ROI performance, stakes are adjusted:

| ROI Range | Multiplier | Meaning |
|-----------|------------|---------|
| > 15% | 2.0x | 🔥 INCREASE - Crushing it! |
| 5-15% | 1.5x | ✅ NORMAL+ - Good performance |
| 0-5% | 1.2x | ✅ NORMAL - Slight edge confirmed |
| 0 to -5% | 0.8x | ⚠️ REDUCE - Barely profitable |
| -5 to -15% | 0.5x | ⚠️ REDUCE - Losing money |
| < -15% | 0.25x | ❌ MINIMIZE - Badly losing |

### 3. Smart Stake Calculation

```
Base Kelly Stake = Standard Kelly Formula
Smart Stake = Base Kelly Stake × Performance Multiplier
Final Stake = min(Smart Stake, Max Stake Limit)
```

## Example Scenario

### Before Smart Staking:
```
NBA 10% edge bet: $50 stake (high edge = high stake)
  → Actually losing 12% ROI
  → Losing $6 per $50 staked

NBA 3% edge bet: $15 stake (low edge = low stake)
  → Actually winning 18% ROI
  → Winning $2.70 per $15 staked
```

### After Smart Staking:
```
NBA 10% edge bet: $50 × 0.5 = $25 stake
  → Multiplier reduces exposure to losing category

NBA 3% edge bet: $15 × 2.0 = $30 stake
  → Multiplier increases exposure to winning category
```

## Viewing Multipliers

When the model runs, you'll see a report like this:

```
📊 SMART STAKING MULTIPLIERS
============================================================

NBA:
  0-3%     ✅ NORMAL         1.20x
  3-6%     🔥 INCREASE       2.00x
  6-10%    ⚠️  REDUCE        0.80x
  10%+     ❌ MINIMIZE       0.25x

NFL:
  0-3%     ✅ NORMAL         1.00x
  3-6%     ✅ NORMAL+        1.50x
  6-10%    ⚠️  REDUCE        0.50x
  10%+     ⚠️  REDUCE        0.50x
```

This tells you:
- NBA 3-6% edge bets are your sweet spot (2x stake)
- NBA 10%+ edge bets are losing badly (0.25x stake)
- Adjust your betting focus accordingly

## Minimum Data Requirements

- **Minimum 10 settled bets** per sport/edge combination
- Uses **last 60 days** of betting history
- Falls back to standard Kelly if insufficient data
- Recalculates every time model runs (always current)

## Benefits

1. **Adaptive Learning**: Stakes adjust as your performance changes
2. **Risk Management**: Automatically reduces exposure to losing categories
3. **Profit Optimization**: Increases exposure to proven winning categories
4. **No Manual Tuning**: System learns from your actual results
5. **Sport-Specific**: Recognizes different sports have different edges

## Dashboard Integration

The Performance by Edge table in the dashboard shows you exactly which edge ranges are performing well, helping you understand why stakes are being adjusted.

## Advanced: Disabling Smart Staking

If you want to temporarily use pure Kelly without performance adjustments, modify `probability_models.py`:

```python
# In calculate_kelly_stake function, change:
use_smart_staking=True  # to False
```

## Testing the System

Run the standalone test:
```bash
python smart_staking.py
```

This will show you current multipliers without running the full model.

## Summary

Smart Staking solves the critical problem of **model miscalibration** by letting your actual results guide stake sizing, not just theoretical edge calculations. It's like having an AI that learns from your wins and losses and adjusts your bet sizing accordingly.
