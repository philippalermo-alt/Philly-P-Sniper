# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Dependencies (1 minute)

```bash
cd ~/Desktop/ncaab_h1_model
pip install -r requirements.txt
```

## Step 2: Set Up API Key (30 seconds)

1. Copy the example env file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your Odds API key:
```bash
ODDS_API_KEY=your_actual_api_key_here
```

Get a free API key at: https://the-odds-api.com/

## Step 3: Test Setup (30 seconds)

```bash
python test_setup.py
```

You should see:
```
🎉 All tests passed! Ready to find edges.
```

If not, follow the instructions provided.

## Step 4: Run Complete Pipeline (5-10 minutes)

### Option A: Automatic (Recommended)

```bash
./run_pipeline.sh
```

This will:
- Collect H1/H2 data from ESPN
- Build team profiles
- Train the model
- Find today's edges

### Option B: Manual (Step-by-step)

```bash
# Collect data
python ncaab_h1_scraper.py

# Train model
python ncaab_h1_train.py

# Find edges
python ncaab_h1_edge_finder.py
```

## Step 5: Review Results

Look for output like:

```
✅ Found 5 betting opportunities:
====================================================================================================
Game                                Book            Bet          Line    Odds   Pred   Edge     EV  Conf
====================================================================================================
Duke vs North Carolina              DraftKings      OVER 68.5    68.5    -110   72.3   8.2%   7.5%   82
Gonzaga vs Saint Mary's             FanDuel         UNDER 71.5   71.5    -115   67.8   7.1%   6.1%   75
====================================================================================================
```

## Daily Usage

Once set up, run this daily to find edges:

```bash
python ncaab_h1_edge_finder.py
```

Best time: 2-4 hours before games start (when H1 lines are posted)

## Weekly Maintenance

Refresh data weekly:

```bash
python ncaab_h1_scraper.py
python ncaab_h1_train.py
```

---

## Troubleshooting

### "ModuleNotFoundError"
- Run: `pip install -r requirements.txt`

### "ODDS_API_KEY not found"
- Create `.env` file
- Add your API key

### "No team profiles found"
- Run: `python ncaab_h1_scraper.py` first

### "No edges found"
- Not all books offer H1 totals
- Check if games are happening today
- Try lowering min_edge threshold

---

## What's Next?

1. **Track results** - Log your bets and outcomes
2. **Adjust thresholds** - Tune min_edge and min_confidence
3. **Compare books** - Shop for best lines
4. **Add to main system** - Integrate with Philly-P-Sniper

---

## Support Files

- `README.md` - Full documentation
- `test_setup.py` - Verify setup
- `run_pipeline.sh` - Automated runner
- `.env.example` - Environment template

---

**Ready to find edges! 🎯**
