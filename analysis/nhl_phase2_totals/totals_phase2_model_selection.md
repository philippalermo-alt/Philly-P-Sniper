# NHL Totals Model Selection Report

| Model | MAE Test | Book MAE Test | Delta (Edge) | Corr vs Market |
|-------|----------|---------------|--------------|----------------|
| Ridge Baseline | 1.8606 | 1.8594 | -0.0012 | 0.660 |
| ElasticNet | 1.8500 | 1.8594 | 0.0094 | 0.918 |
| GradientBoosting | 1.8639 | 1.8594 | -0.0045 | 0.328 |


## Recommendation
The best performing model is **ElasticNet** with Test MAE 1.8500.
