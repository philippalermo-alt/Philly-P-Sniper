# NHL Totals Phase 2 Calibration Report

## 1. Global Parameters (Validation Set)
- **Model**: ElasticNet (alpha=0.1, l1=0.5)
- **Bias Correction Applied**: -0.1433
- **Global Sigma (Std Dev)**: 2.2420
- **Final Bias**: -0.0000 (Expected ~0)

## 2. Bucket Analysis (Sigma Stability)
             count       std      mean
line_bucket                           
6.0            424  2.257223  0.008494
6.5            213  2.274026  0.075998
<= 5.5         365  2.212214 -0.050815
>= 7.0           1       NaN -1.241169

## 3. Histogram of Residuals
(Residuals distribution assumed roughly Normal around 0 with sigma=2.24)

## 4. Probability Check (Sample)
First 5 Validation Rows:
           date  total_line_close  expected_total  prob_over  prob_under  total_goals
3019 2024-11-08               6.5        6.237986   0.453483    0.546517          6.0
3020 2024-11-08               6.0        5.977478   0.495992    0.504008          4.0
3021 2024-11-08               6.0        6.014098   0.502509    0.497491          7.0
3022 2024-11-09               6.5        6.310575   0.466334    0.533666          4.0
3023 2024-11-09               6.5        6.100561   0.429298    0.570702         10.0

## 5. Decision
Recommended Sigma: **2.2420** (Global).
Bucketed Sigmas show STABILITY.
