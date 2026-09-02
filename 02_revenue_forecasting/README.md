# Revenue Forecasting (Trend + Seasonality)

Forecasts the next 12 months of revenue from 36 months of history by
decomposing it into a growth trend and a repeating seasonal pattern, with a
confidence band around the forecast.

## Business problem

Revenue rarely grows in a straight line — most businesses have a
within-year seasonal pattern layered on top of an underlying growth trend.
A naive forecast (last year + X%) misses the seasonal swing; this model
separates the two so both are visible and the forecast reflects both.

## What this script does

`forecast.py`:

1. Fits a log-linear trend to historical revenue (captures compounding
   growth as a straight line in log-space).
2. Computes an average seasonal index per calendar month from the
   detrended residuals.
3. Projects the next N months (default 12) by extending the trend and
   reapplying the matching month's seasonal index.
4. Builds an 80% confidence band from the in-sample residual standard
   deviation.
5. Exports the forecast as CSV and a chart showing history, forecast, and
   the confidence band.

## Run it

```bash
python forecast.py
```

```bash
python forecast.py --data-dir ../data --output-dir ./sample_output --horizon 12
```

## Sample output

```
  Fitted monthly trend growth: 1.29%
  Next 12-month forecast revenue : $30,156,196

  2026-09: $2,137,161  (80% band: $2,082,523 - $2,191,799)
  2026-10: $2,100,750  (80% band: $2,046,112 - $2,155,389)
  ...
```

See [`sample_output/`](./sample_output) for the full forecast table and
`forecast_chart.png`.

## How this maps to real-world FP&A / BA work

This is a lightweight, dependency-free stand-in for the kind of forecasting
models used in budgeting and forecast-to-actual reviews. In production you'd
swap in a proper time-series library (statsmodels, Prophet) or plug in
external drivers (pipeline, bookings), but the trend/seasonality separation
and the confidence-band habit carry over directly.
