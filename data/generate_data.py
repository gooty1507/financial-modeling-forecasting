"""
generate_data.py

Generates fully SYNTHETIC financial data used by the DCF valuation model and
the revenue forecasting model in this repo. Nothing here is real company
data -- it's randomly generated with a fixed seed so results are
reproducible.

Run this once before using either sub-project:

    python data/generate_data.py

Outputs:
    historical_financials.csv  -- 5 years of annual P&L / cash flow drivers
    assumptions.csv            -- valuation assumptions (WACC, growth, tax)
    monthly_revenue.csv        -- 36 months of revenue history w/ seasonality
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 7
rng = np.random.default_rng(SEED)
OUT_DIR = Path(__file__).parent

# ---------------------------------------------------------------------------
# 5 years of annual historical financials (for the DCF model)
# ---------------------------------------------------------------------------

years = list(range(2021, 2026))
revenue = [18_500_000]
for _ in range(len(years) - 1):
    revenue.append(round(revenue[-1] * rng.uniform(1.08, 1.22)))

rows = []
for yr, rev in zip(years, revenue):
    cogs_pct = rng.uniform(0.42, 0.48)
    opex_pct = rng.uniform(0.28, 0.34)
    capex_pct = rng.uniform(0.03, 0.06)
    da_pct = rng.uniform(0.025, 0.04)
    nwc_change_pct = rng.uniform(0.01, 0.025)
    rows.append({
        "year": yr,
        "revenue": rev,
        "cogs": round(rev * cogs_pct),
        "opex": round(rev * opex_pct),
        "capex": round(rev * capex_pct),
        "depreciation_amortization": round(rev * da_pct),
        "nwc_change": round(rev * nwc_change_pct),
    })

historical = pd.DataFrame(rows)
historical.to_csv(OUT_DIR / "historical_financials.csv", index=False)

# ---------------------------------------------------------------------------
# Valuation assumptions (for the DCF model)
# ---------------------------------------------------------------------------

assumptions = pd.DataFrame([
    {"assumption": "forecast_years", "value": 5},
    {"assumption": "revenue_growth_rate", "value": 0.10},   # 10% p.a. forecast growth
    {"assumption": "cogs_pct_of_revenue", "value": 0.45},
    {"assumption": "opex_pct_of_revenue", "value": 0.30},
    {"assumption": "capex_pct_of_revenue", "value": 0.045},
    {"assumption": "da_pct_of_revenue", "value": 0.032},
    {"assumption": "nwc_change_pct_of_revenue", "value": 0.018},
    {"assumption": "tax_rate", "value": 0.24},
    {"assumption": "wacc", "value": 0.095},
    {"assumption": "terminal_growth_rate", "value": 0.025},
    {"assumption": "net_debt", "value": 4_200_000},
    {"assumption": "shares_outstanding", "value": 2_500_000},
])
assumptions.to_csv(OUT_DIR / "assumptions.csv", index=False)

# ---------------------------------------------------------------------------
# 36 months of revenue history with trend + seasonality (for forecasting)
# ---------------------------------------------------------------------------

n_months = 36
month_index = np.arange(n_months)
base = 1_500_000
trend = base * (1 + 0.012) ** month_index                       # ~1.2%/month growth
seasonality = 1 + 0.10 * np.sin(2 * np.pi * (month_index % 12) / 12 - np.pi / 2)  # dip in Q1, peak in Q3
noise = rng.normal(1.0, 0.035, size=n_months)
monthly_revenue_values = (trend * seasonality * noise).round(0)

dates = pd.date_range(end=pd.Timestamp("2026-08-01"), periods=n_months, freq="MS")
monthly_revenue = pd.DataFrame({
    "month": dates.strftime("%Y-%m"),
    "revenue": monthly_revenue_values.astype(int),
})
monthly_revenue.to_csv(OUT_DIR / "monthly_revenue.csv", index=False)

print("Synthetic data generated in:", OUT_DIR)
print(f"  historical_financials.csv : {len(historical)} rows")
print(f"  assumptions.csv            : {len(assumptions)} rows")
print(f"  monthly_revenue.csv        : {len(monthly_revenue)} rows")
