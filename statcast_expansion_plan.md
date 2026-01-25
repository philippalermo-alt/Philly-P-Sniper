# 🧪 Statcast Feature Expansion Plan (Morning Session)

**Current Status:** The core Engine is solid (-1.0% vs Vig).
**Next Goal:** Capture the "Contextual Edge" (+3-4% ROI) by ingesting game-specific variables effectively.

Here are 4 concrete proposals for data we can extract from Statcast/MLB API to upgrade the model.

---

## 🏗 Proposal 1: The "Active 9" Whiff Load
**The Problem:** Our model currently uses `Opponent Team Rolling Whiff %`. This treats the NY Yankees the same whether Judge/Soto are playing or resting.
**The Fix:** Calculate a dynamic "Lineup Whiff Score" based on the actual 9 batters.

*   **Data Source:** `mlbstatsapi` (Lineup Endpoint) + Statcast Batter Data.
*   **Method:**
    1.  Fetch efficient daily lineups (`/game/{game_pk}/boxscore` approx 2h before first pitch).
    2.  Map each `batter_id` to their rolling `Whiff%` vs RHP/LHP.
    3.  Compute `Weighted_Lineup_K_Prob`.
*   **Hypothesis:** Betting Overs against a "Sunday Lineup" (Weak C-team) is a classic trap our current model falls into. This fixes it.

---

## 👨‍⚖️ Proposal 2: The "Shadow Zone" Umpire Factor
**The Problem:** A "Pitcher's Umpire" who expands the zone by 1 inch adds ~0.5 to 1.0 Ks per game. Our model assumes a neutral zone.
**The Fix:** Build an Umpire Tendency Feature from historical Statcast pitch data.

*   **Data Source:** Historical Statcast (`description` = "called_strike" vs "ball", `plate_x`, `plate_z`).
*   **Method:**
    1.  Filter pitches in the "Shadow Zone" (Edges of the plate).
    2.  Calculate `Called_Strike_Rate` for each Umpire ID.
    3.  Join this feature to the game.
*   **Hypothesis:** If Umpire X calls strikes 60% of the time in the Shadow Zone (Avg 48%), bump the projection by +0.8 Ks.

---

## 📉 Proposal 3: Velocity Decay Flag (Injury/Fatigue Check)
**The Problem:** Our model sees a pitcher with great rolling stats, but doesn't know his fastball dropped 2.5 mph in the 5th inning of his last start (injury warning).
**The Fix:** Feature Engineering on `release_speed`.

*   **Data Source:** Rolling Statcast Pitch Data.
*   **Method:**
    1.  Calculate `Avg_Fastball_Velo` for the *Last Start*.
    2.  Compare to `Season_Avg_Velo`.
    3.  **Feature:** `Velo_Dip` (e.g. -1.5 mph).
*   **Hypothesis:** Significant velocity dips are the #1 predictor of "Short Leash" blowups. This feeds directly into our Alpha/Leash logic to kill bad Over bets.

---

## ☁️ Proposal 4: Atmospheric "Stuff" Index
**The Problem:** A curveball breaks less in Coors Field (Low Density) or hot Texas air than in cold San Francisco air. "Stuff Quality" varies by day.
**The Fix:** Adjust `expected_whiff` based on air density.

*   **Data Source:** MLB Game Weather (Temp, Altitude from Stadium ID).
*   **Method:**
    1.  Calculate `Air_Density_Index`.
    2.  Correlate with `Vertical_Break_Induced`.
    3.  **Feature:** `Predicted_Break_Adjustment`.
*   **Complexity:** High. Requires physics modeling.
*   **Alternative:** Just use `Park_Factor_K` (Statcast Park Factors).

---

## 🚀 Recommendation for Morning
Start with **Proposal 1 (Active 9)**. It is the lowest hanging fruit with the highest impact. Lineups change daily, and "Rest Days" provide massive edges that Vegas algorithms sometimes lag on (or our model currently misses).

Get some sleep! We attack the lineups at dawn. ☕️
