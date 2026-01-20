# 🧠 Model V2 Training FAQ

**Last Updated:** January 2026
**Model Type:** Logistic Regression (Scikit-Learn)

---

## 📅 When should I run the first training?
**Recommendation:** After **50-100 graded bets** have accumulated since the Phase 2 upgrade.

### Why wait?
The new model uses these specific features:
1.  **xG Diff** (Soccer)
2.  **DvP Rank** (NBA)
3.  **Sharp Money %**

Your historical data (before today) *does not* have these columns populated. If you train now, the model will see mostly `0`s for these features, leading to a "garbage in, garbage out" situation.

---

## 🛠️ How do I train the model?
Since your app is hosted on **Heroku**, you must run the training script in the cloud (not on your local Mac).

### Step-by-Step Command
Run this in your terminal:
```bash
heroku run python3 -m models.train_v2
```

### What happens next?
1.  The script connects to your Heroku Postgres database.
2.  It loops through **NBA, Soccer, NCAAB** and other sports.
3.  It pulls all `WON` and `LOST` bets for that sport.
4.  It trains a specific model for each sport (e.g., `models/nba_model.pkl` using DvP, `models/ncaab_model.pkl` using KenPom).
5.  It outputs the **Accuracy** and **Log Loss** for each.
6.  It saves the model file (`models/v2_logistic.pkl`) *temporarily* in the Heroku dyno.

> **⚠️ CRITICAL NOTE for Heroku:**
> Heroku filesystems are **ephemeral**. The `.pkl` file created above will vanish when the dyno restarts (every 24h or on deploy).
>
> **For Phase 3 (Future):** We will need to save the model to **AWS S3** or store the coefficients directly in the Database so they persist.
>
> **For Now (Interim Solution):**
> run the script to **see the coefficients**, then manually update your code if you want to "lock in" the weights, OR run the training specifically before a big batch of bets if you want to use the file immediately.

---

## 🔄 How often should I retrain?
*   **Initially:** Once a week (every Monday).
*   **Long-term:** Once a month.

Over-training (every hour) is bad because it might chase short-term variance.

---

## 📊 How do I know if it's working?
When you run the command, look for the **Coefficients** output.

*   **Positive Coefficient (e.g., +0.5):** Increases probability of winning.
*   **Negative Coefficient (e.g., -0.2):** Decreases probability.

**Example of Healthy Output:**
```
Feature           Coefficient
implied_prob      +2.10   (Market odds are strong)
my_prob           +0.85   (Your math adds value)
sharp_money_pct   +0.30   (Sharp money helps)
dvp_rank          +0.05   (Defense rank has minor impact)
```

If `implied_prob` is close to 0, something is wrong (the model isn't respecting the bookmaker's odds).
