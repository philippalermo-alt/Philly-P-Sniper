# Scraper Testing Notes

## ✅ Scraper Verified Working

The scraper has been tested and confirmed working with ESPN's API.

### Test Results:

**API Endpoints:**
- ✅ Scoreboard API: `https://site.api.espn.com/.../scoreboard` - Working
- ✅ Game Summary API: `https://site.api.espn.com/.../summary?event=ID` - Working
- ✅ H1/H2 Linescore Extraction: Working correctly

**Test Data (Jan 21, 2026 games):**
```
✓ Arizona Wildcats vs Cincinnati Bearcats
  H1 Total: 60 | H2 Total: 68

✓ Nebraska Cornhuskers vs Washington Huskies
  H1 Total: 69 | H2 Total: 73

✓ Gonzaga Bulldogs vs Pepperdine Waves
  H1 Total: 76 | H2 Total: 68
```

All games fetched successfully with correct H1/H2 splits.

---

## 📊 Data Requirements

To build usable team profiles, you need:

- **Minimum games per team:** 3 (configurable in code)
- **Recommended total games:** 500+ for good coverage
- **Time period:** 60 days gives ~800-1000 completed games

### Why 500 games?

- NCAAB has ~350 Division I teams
- Each game = 2 teams
- 500 games = 1000 team-game observations
- Average: ~2.8 games per team
- With 3-game minimum: ~200-250 teams will have profiles

---

## ⚙️ Configuration Changes Made

### 1. Minimum Games Threshold
Changed from 5 → 3 games minimum for faster setup:

```python
# Line 173 in ncaab_h1_scraper.py
if stats['games_played'] < 3:  # Was 5
```

### 2. Data Collection Range
Increased to fetch more games:

```python
# Line 207
games = self.fetch_schedule(date_range_days=60)  # Was 45
max_games = 500  # Was 300
```

---

## 🚀 First-Time Setup

When running for the first time:

```bash
python ncaab_h1_scraper.py
```

**Expected:**
- Time: 5-10 minutes
- Games fetched: 500
- Teams with profiles: 200-250
- API calls: ~560 (1 for each day + 1 per game)

**Note:** ESPN's API is public and doesn't require authentication, but be respectful with rate limiting (0.2s between requests).

---

## 🔍 Data Structure

### Linescore Location
Found in: `header → competitions[0] → competitors → linescores`

```json
{
  "linescores": [
    {"displayValue": "33"},  // H1 score
    {"displayValue": "44"}   // H2 score (includes OT if applicable)
  ]
}
```

### Team Identification
- `homeAway` field determines home/away
- Fallback: First competitor = home, second = away

---

## ✅ Verification

To test the scraper is working:

```python
from ncaab_h1_scraper import NCAAB_H1_Scraper

scraper = NCAAB_H1_Scraper()

# Test single game
game_id = "401827637"  # Example game ID
result = scraper.fetch_game_details(game_id)

if result:
    print(f"H1 Total: {result['h1_total']}")
    print(f"H2 Total: {result['h2_total']}")
```

Expected: Should print actual scores, not `None`.

---

## 🛠️ Troubleshooting

### "No team profiles found"
**Cause:** Not enough games fetched, or teams don't have 3+ games

**Fix:**
- Increase `date_range_days` to 90
- Or lower minimum threshold to 2 games

### "Connection timeout"
**Cause:** ESPN API temporarily unavailable

**Fix:**
- Wait a few minutes and retry
- Check internet connection

### "All profiles have 1-2 games"
**Cause:** Not fetching enough total games

**Fix:**
- Increase `max_games` to 700-1000
- Fetch more days of data

---

## 📅 Season Coverage

**Best Time to Run:**
- **January - March:** Full season data, 300+ teams available
- **November - December:** Early season, limited data (<20 games/team)
- **April+:** Season over, use prior season data

**Current Testing:** Mid-January 2026 - Excellent data availability

---

**Last Updated:** January 22, 2026
**Status:** ✅ Fully tested and working
