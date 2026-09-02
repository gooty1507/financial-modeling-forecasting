"""
forecast.py -- Revenue forecasting with trend + seasonality decomposition.

Mirrors the resume's "Forecasting Models" and "Model risk-adjusted financial
scenarios using Python automation" bullets.

What it does
------------
1. Loads 36 months of historical revenue.
2. Fits a log-linear trend (captures compounding growth) plus a monthly
   seasonal index (captures the recurring within-year pattern), using
   straightforward numpy regression -- no exotic dependencies required.
3. Projects the next 12 months forward, reapplying the seasonal pattern.
4. Builds a simple confidence band from the in-sample residual standard
   deviation (a lightweight stand-in for a full prediction interval).
5. Exports the forecast as a CSV and a chart showing history, forecast, and
   the confidence band -- the kind of chart that goes straight into a
   forecast-to-actual review deck.

Usage
-----
    python forecast.py
    python forecast.py --data-dir ../data --output-dir ./sample_output --horizon 12
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent


def fit_trend_and_seasonality(df: pd.DataFrame):
    """Fit log-linear trend + additive monthly seasonal index."""
    df = df.copy()
    df["t"] = np.arange(len(df))
    df["month_num"] = pd.to_datetime(df["month"]).dt.month
    df["log_revenue"] = np.log(df["revenue"])

    # Trend: linear regression on log(revenue) ~ t
    slope, intercept = np.polyfit(df["t"], df["log_revenue"], 1)
    df["trend_log"] = intercept + slope * df["t"]
    df["detrended"] = df["log_revenue"] - df["trend_log"]

    # Seasonality: average detrended log-residual per calendar month
    seasonal_index = df.groupby("month_num")["detrended"].mean()

    df["fitted_log"] = df["trend_log"] + df["month_num"].map(seasonal_index)
    df["fitted"] = np.exp(df["fitted_log"])
    df["residual"] = df["revenue"] - df["fitted"]

    return slope, intercept, seasonal_index, df


def main():
    parser = argparse.ArgumentParser(description="Forecast revenue using trend + seasonality decomposition.")
    parser.add_argument("--data-dir", default=str(HERE.parent / "data"))
    parser.add_argument("--output-dir", default=str(HERE / "sample_output"))
    parser.add_argument("--horizon", type=int, default=12, help="Months to forecast forward")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    hist = pd.read_csv(data_dir / "monthly_revenue.csv")
    hist["month"] = pd.to_datetime(hist["month"])

    slope, intercept, seasonal_index, fitted_hist = fit_trend_and_seasonality(hist)
    residual_std = fitted_hist["residual"].std()

    # --- Build forward forecast ---------------------------------------
    n_hist = len(hist)
    future_t = np.arange(n_hist, n_hist + args.horizon)
    future_months = pd.date_range(hist["month"].max() + pd.offsets.MonthBegin(1), periods=args.horizon, freq="MS")
    future_month_num = future_months.month

    trend_log = intercept + slope * future_t
    seasonal_component = np.array([seasonal_index.get(m, 0.0) for m in future_month_num])
    forecast_log = trend_log + seasonal_component
    forecast_values = np.exp(forecast_log)

    forecast_df = pd.DataFrame({
        "month": future_months.strftime("%Y-%m"),
        "forecast_revenue": forecast_values.round(0).astype(int),
        "lower_80": (forecast_values - 1.28 * residual_std).round(0).astype(int),
        "upper_80": (forecast_values + 1.28 * residual_std).round(0).astype(int),
    })
    forecast_df.to_csv(output_dir / "forecast.csv", index=False)

    monthly_growth_pct = (np.exp(slope) - 1)
    total_hist = hist.revenue.sum()
    total_forecast = forecast_df.forecast_revenue.sum()

    print("=" * 60)
    print(f"REVENUE FORECAST  ({args.horizon}-month horizon)")
    print("=" * 60)
    print(f"  Historical months analyzed : {n_hist}")
    print(f"  Fitted monthly trend growth: {monthly_growth_pct:.2%}")
    print(f"  In-sample residual std dev : ${residual_std:,.0f}")
    print(f"  Trailing {n_hist}-month actual revenue : ${total_hist:,.0f}")
    print(f"  Next {args.horizon}-month forecast revenue : ${total_forecast:,.0f}")
    print("\n  First 6 months of forecast:")
    for _, row in forecast_df.head(6).iterrows():
        print(f"    {row.month}: ${row.forecast_revenue:>10,}  "
              f"(80% band: ${row.lower_80:,} - ${row.upper_80:,})")

    # --- Chart: history + forecast + confidence band ------------------
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(hist["month"], hist["revenue"], label="Historical revenue", color="#2c3e50", linewidth=2)
    ax.plot(future_months, forecast_df.forecast_revenue, label="Forecast", color="#c0392b",
            linewidth=2, linestyle="--")
    ax.fill_between(future_months, forecast_df.lower_80, forecast_df.upper_80,
                     color="#c0392b", alpha=0.15, label="80% confidence band")
    ax.axvline(hist["month"].max(), color="gray", linewidth=0.8, linestyle=":")
    ax.set_title("Monthly Revenue: History + 12-Month Forecast")
    ax.set_ylabel("Revenue ($)")
    ax.legend()
    ax.yaxis.set_major_formatter(lambda x, pos: f"${x/1e6:.1f}M")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output_dir / "forecast_chart.png", dpi=150)
    plt.close(fig)

    print(f"\nDetailed output written to: {output_dir}")
    print("  - forecast.csv")
    print("  - forecast_chart.png")


if __name__ == "__main__":
    main()
