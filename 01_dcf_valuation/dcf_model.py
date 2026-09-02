"""
dcf_model.py -- Discounted Cash Flow valuation with sensitivity analysis.

Mirrors the resume's "Financial Modeling: DCF, ROI, Cost & Profitability
Modeling, Forecasting Models" and "Scenario & Sensitivity Analysis" bullets.

What it does
------------
1. Loads 5 years of historical financials and a set of valuation assumptions
   (growth rate, margins, WACC, terminal growth, tax rate).
2. Projects unlevered free cash flow for the next N forecast years:
       FCF = EBIT * (1 - tax rate) + D&A - capex - change in NWC
3. Discounts each year's FCF back to present value at the WACC, adds a
   Gordon Growth terminal value, and derives:
       Enterprise Value -> Equity Value -> Implied share price
4. Runs a 2-D sensitivity grid (WACC x terminal growth rate) so you can see
   how much the valuation swings with the assumptions -- the standard
   "how confident are we in this number" check any DCF needs.
5. Exports the projection, the valuation summary, and the sensitivity grid
   as CSVs, plus a heatmap PNG of the sensitivity grid.

Usage
-----
    python dcf_model.py
    python dcf_model.py --data-dir ../data --output-dir ./sample_output
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).parent


def load_assumptions(data_dir: Path) -> dict:
    df = pd.read_csv(data_dir / "assumptions.csv")
    return dict(zip(df.assumption, df.value))


def project_cash_flows(historical: pd.DataFrame, a: dict) -> pd.DataFrame:
    last_year = int(historical.year.max())
    last_revenue = float(historical.loc[historical.year == last_year, "revenue"].iloc[0])

    rows = []
    revenue = last_revenue
    for i in range(1, int(a["forecast_years"]) + 1):
        year = last_year + i
        revenue = revenue * (1 + a["revenue_growth_rate"])
        cogs = revenue * a["cogs_pct_of_revenue"]
        opex = revenue * a["opex_pct_of_revenue"]
        ebit = revenue - cogs - opex
        capex = revenue * a["capex_pct_of_revenue"]
        da = revenue * a["da_pct_of_revenue"]
        nwc_change = revenue * a["nwc_change_pct_of_revenue"]
        nopat = ebit * (1 - a["tax_rate"])
        fcf = nopat + da - capex - nwc_change

        rows.append({
            "year": year, "revenue": round(revenue), "ebit": round(ebit),
            "nopat": round(nopat), "d_and_a": round(da), "capex": round(capex),
            "nwc_change": round(nwc_change), "free_cash_flow": round(fcf),
        })

    return pd.DataFrame(rows)


def discount_cash_flows(projection: pd.DataFrame, wacc: float, terminal_growth: float, net_debt: float, shares: float) -> dict:
    n = len(projection)
    discount_factors = [(1 + wacc) ** -(i + 1) for i in range(n)]
    pv_fcf = (projection.free_cash_flow.values * discount_factors).sum()

    final_fcf = projection.free_cash_flow.iloc[-1]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
    pv_terminal_value = terminal_value * discount_factors[-1]

    enterprise_value = pv_fcf + pv_terminal_value
    equity_value = enterprise_value - net_debt
    price_per_share = equity_value / shares

    return {
        "pv_of_explicit_fcf": round(pv_fcf),
        "terminal_value": round(terminal_value),
        "pv_of_terminal_value": round(pv_terminal_value),
        "enterprise_value": round(enterprise_value),
        "net_debt": round(net_debt),
        "equity_value": round(equity_value),
        "shares_outstanding": round(shares),
        "implied_price_per_share": round(price_per_share, 2),
        "terminal_value_pct_of_ev": round(pv_terminal_value / enterprise_value, 4),
    }


def sensitivity_grid(projection: pd.DataFrame, base_wacc: float, base_tgr: float, net_debt: float, shares: float) -> pd.DataFrame:
    wacc_range = [base_wacc + d for d in (-0.015, -0.0075, 0, 0.0075, 0.015)]
    tgr_range = [base_tgr + d for d in (-0.01, -0.005, 0, 0.005, 0.01)]

    grid = pd.DataFrame(index=[f"{w:.2%}" for w in wacc_range], columns=[f"{g:.2%}" for g in tgr_range])
    for w in wacc_range:
        for g in tgr_range:
            if w <= g:
                value = np.nan  # not economically valid (WACC must exceed terminal growth)
            else:
                result = discount_cash_flows(projection, w, g, net_debt, shares)
                value = result["implied_price_per_share"]
            grid.loc[f"{w:.2%}", f"{g:.2%}"] = value

    grid.index.name = "WACC \\ Terminal Growth"
    return grid


def main():
    parser = argparse.ArgumentParser(description="Run a DCF valuation with sensitivity analysis.")
    parser.add_argument("--data-dir", default=str(HERE.parent / "data"))
    parser.add_argument("--output-dir", default=str(HERE / "sample_output"))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    historical = pd.read_csv(data_dir / "historical_financials.csv")
    a = load_assumptions(data_dir)

    projection = project_cash_flows(historical, a)
    projection.to_csv(output_dir / "fcf_projection.csv", index=False)

    valuation = discount_cash_flows(projection, a["wacc"], a["terminal_growth_rate"], a["net_debt"], a["shares_outstanding"])
    pd.DataFrame([valuation]).to_csv(output_dir / "valuation_summary.csv", index=False)

    grid = sensitivity_grid(projection, a["wacc"], a["terminal_growth_rate"], a["net_debt"], a["shares_outstanding"])
    grid.to_csv(output_dir / "sensitivity_grid.csv")

    # --- Console summary ---------------------------------------------------
    print("=" * 60)
    print("DCF VALUATION")
    print("=" * 60)
    print(f"  Forecast horizon      : {int(a['forecast_years'])} years")
    print(f"  Revenue growth (fcst) : {a['revenue_growth_rate']:.1%} p.a.")
    print(f"  WACC                  : {a['wacc']:.2%}")
    print(f"  Terminal growth rate  : {a['terminal_growth_rate']:.2%}")
    print()
    print(f"  PV of explicit FCF    : ${valuation['pv_of_explicit_fcf']:,}")
    print(f"  PV of terminal value  : ${valuation['pv_of_terminal_value']:,}  ({valuation['terminal_value_pct_of_ev']:.1%} of EV)")
    print(f"  Enterprise value      : ${valuation['enterprise_value']:,}")
    print(f"  Less: net debt        : ${valuation['net_debt']:,}")
    print(f"  Equity value          : ${valuation['equity_value']:,}")
    print(f"  Implied price/share   : ${valuation['implied_price_per_share']:,.2f}")

    # --- Sensitivity heatmap -------------------------------------------
    numeric_grid = grid.astype(float)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    im = ax.imshow(numeric_grid.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(numeric_grid.columns)))
    ax.set_xticklabels(numeric_grid.columns)
    ax.set_yticks(range(len(numeric_grid.index)))
    ax.set_yticklabels(numeric_grid.index)
    ax.set_xlabel("Terminal Growth Rate")
    ax.set_ylabel("WACC")
    ax.set_title("Implied Price per Share -- Sensitivity to WACC & Terminal Growth")
    for i in range(numeric_grid.shape[0]):
        for j in range(numeric_grid.shape[1]):
            val = numeric_grid.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"${val:,.0f}", ha="center", va="center", fontsize=9)
    fig.colorbar(im, ax=ax, label="Implied price/share ($)")
    fig.tight_layout()
    fig.savefig(output_dir / "dcf_sensitivity.png", dpi=150)
    plt.close(fig)

    print(f"\nDetailed output written to: {output_dir}")
    print("  - fcf_projection.csv")
    print("  - valuation_summary.csv")
    print("  - sensitivity_grid.csv")
    print("  - dcf_sensitivity.png")


if __name__ == "__main__":
    main()
