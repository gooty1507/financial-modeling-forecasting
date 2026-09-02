# DCF Valuation with Sensitivity Analysis

A discounted cash flow model that projects free cash flow, discounts it back
at WACC, and stress-tests the valuation against a grid of WACC / terminal
growth assumptions.

## Business problem

A single-point DCF valuation is only as good as its assumptions — and WACC
and terminal growth rate are exactly the two inputs analysts argue about
most, because the valuation is highly sensitive to both. Presenting one
number without showing that sensitivity is a common (and misleading)
shortcut.

## What this script does

`dcf_model.py`:

1. Projects 5 years of unlevered free cash flow from historical financials
   and a set of growth/margin assumptions:
   `FCF = EBIT × (1 − tax rate) + D&A − capex − Δ NWC`
2. Discounts each year's FCF at WACC and adds a Gordon Growth terminal
   value to get Enterprise Value → Equity Value → implied price per share.
3. Recomputes the valuation across a 5×5 grid of WACC and terminal growth
   rate combinations and renders it as a heatmap.

## Run it

```bash
python dcf_model.py
```

```bash
python dcf_model.py --data-dir ../data --output-dir ./sample_output
```

## Sample output

```
  PV of explicit FCF    : $27,727,282
  PV of terminal value  : $81,942,880  (74.7% of EV)
  Enterprise value      : $109,670,161
  Equity value           : $105,470,161
  Implied price/share   : $42.19
```

See [`sample_output/`](./sample_output) for the full projection, valuation
summary, sensitivity grid, and heatmap (`dcf_sensitivity.png`).

## How this maps to real-world FP&A / BA work

This is the same structure behind an ROI or cost/profitability model used to
support pricing or investment decisions — the assumptions block
(`data/assumptions.csv`) is deliberately separated from the model logic so
it can be swapped for scenario/sensitivity runs, the same pattern used for
"risk-adjusted financial scenarios" and gross margin / customer
profitability analysis.
