# CMG Valuation Model

A DCF and comparable companies valuation of Chipotle Mexican Grill (NYSE: CMG), built in Python with live data from [yfinance](https://github.com/ranaroussi/yfinance).

**TL;DR:** As of the last data pull, CMG traded at **$36.95**. This model's base-case DCF implies **$19.98/share**, and a comps-based range (peer EV/Revenue and EV/EBITDA multiples applied to CMG) implies **$9.85–$75.54**, median-multiple midpoint around **$31**. In short: the market is pricing in more growth/durability than a conservative base case captures — see [Interpreting the gap](#interpreting-the-gap-to-market-price) below for why, and the [sensitivity table](#sensitivity-wacc-vs-terminal-growth) for what assumptions would justify the current price. At the generous corner of that grid the DCF reaches $35.90, close enough to the market price that the remaining disagreement is about assumptions rather than arithmetic.

![Valuation summary](outputs/figures/valuation_summary.png)

## What this is

Two independent valuation approaches, each in its own module, tied together by one script:

1. **DCF** — projects CMG's revenue, margins, and free cash flow for 5 years, discounts them (plus a terminal value) back to a present enterprise value, then bridges to an implied share price.
2. **Comparable companies ("comps")** — takes trading multiples (EV/Revenue, EV/EBITDA, P/E) from six public fast-casual/restaurant peers and applies them to CMG's own financials to imply a valuation range.

Neither approach is "the answer" — they're two different lenses, and the gap between them (and vs. the current market price) is itself the interesting output.

## Repo structure

```
config/assumptions.yaml     All inputs in one place — growth rates, margins, WACC components, comp set
src/data/fetch.py           Pulls & locally caches financials via yfinance (reproducible re-runs)
src/dcf/                    Revenue/FCF projection, WACC, terminal value, EV->equity bridge, sensitivity
src/comps/                  Peer multiples table, implied valuation from comps
src/output/                 Chart and table generation
main.py                     Runs the full pipeline end to end
notebooks/walkthrough.ipynb Thin, narrated notebook over the same src/ modules (no separate logic)
outputs/                    Generated tables (CSV + Markdown) and charts (PNG)
tests/test_dcf.py           Sanity checks on the DCF math and the equity bridge
tests/test_comps.py         Checks on peer eligibility — which multiples are meaningful
```

## How to run it

```bash
python -m venv .venv
.venv\Scripts\activate        # or: source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python main.py
```

This regenerates everything in `outputs/`. Data pulled from yfinance is cached to `src/data/cache/` by pull date, so re-running the same day reuses the cached snapshot instead of hitting the network — and the cached files are committed, so the results in this README are reproducible even without a live data pull.

Run the test suite with:

```bash
pytest tests/
```

## Methodology & assumptions

Every number below lives in [`config/assumptions.yaml`](config/assumptions.yaml) — nothing is hardcoded inside the calculation logic.

### Revenue growth

| | FY2026 | FY2027 | FY2028 | FY2029 | FY2030 |
|---|---|---|---|---|---|
| Growth | 9.2% | 10.0% | 9.0% | 8.0% | 7.0% |

CMG's revenue growth decelerated sharply in FY2025 (+5.4%, down from +14.3% in FY2024 and +14.4% in FY2023) amid a well-documented comp-sales slowdown. Year 1–2 anchor to analyst consensus (+9.2% / +10.8%, pulled from yfinance), then the growth rate fades toward a more sustainable long-run pace as the restaurant base matures — a standard fade pattern for a maturing growth compounder.

### Margins & reinvestment

- **Operating margin**: holds around 16.5%, drifting to 17.5% by Year 5 — within CMG's actual 4-year range of 14.0%–17.5%, assuming modest ongoing operating leverage rather than a big margin inflection either way.
- **CapEx**: ~5.5% of revenue tapering to 5.0%, matching the recent 4-year average; funds continued new-restaurant growth.
- **D&A**: held flat at ~3.0% of revenue, matching recent actuals.
- **Net working capital**: 2.0% of the *change* in revenue, not of the revenue level. NWC is a balance-sheet stock, so only its year-over-year movement is a cash flow — charging a percentage of total revenue every year would bill the business again and again for working capital it already funded. 2.0% of incremental revenue is deliberately cautious for this business: CMG collects from guests at the register and pays suppliers on terms, so it actually runs *negative* working capital and growth arguably releases cash. Setting the assumption negative in the config models that; the base case stays conservative.
- **Tax rate**: 25%, slightly above the trailing effective rate of 23.6% — a deliberately conservative round number.

### Cost of capital (WACC)

CMG carries **no traditional bonds or bank debt**. The ~$5.1B of "debt" on its balance sheet is entirely capitalized operating lease liabilities (nearly all its restaurants are leased, not owned or financed conventionally), and lease expense is already embedded above the operating-income line.

Given that, WACC is set equal to the **CAPM cost of equity**, treating CMG as effectively all-equity-funded — the more common practitioner treatment for restaurant chains in this situation:

```
Cost of equity = Risk-free rate + Beta × Equity risk premium
              = 4.8%          + 0.94 × 5.0%
              = 9.49%
```

- **Risk-free rate**: current 10-year US Treasury yield (4.8%)
- **Beta**: 0.94, CMG's 5-year monthly beta per yfinance
- **Equity risk premium**: 5.0%, a standard long-run US equity risk premium

*Alternative considered:* capitalizing the lease liability as debt in the WACC weights (using CMG's lease discount rate, ~4.5%, as pre-tax cost of debt) instead moves WACC to roughly 8.9% — a small effect, since the implied debt weight is only ~10% of enterprise value. The simpler all-equity treatment is used throughout, but this is a legitimate point of debate and worth knowing about if you disagree with it.

### The lease decision, and why the bridge is consistent with it

This is the one choice that most moves the answer, so it lives in its own module, [`src/dcf/equity_bridge.py`](src/dcf/equity_bridge.py), rather than as a bare subtraction inside `main.py`.

Rent expense is **already deducted above the operating-income line**. That means the economic cost of CMG's leases is already inside the unlevered free cash flow this model discounts. Subtracting the ~$5.4B capitalized lease liability *again* in the enterprise-value-to-equity bridge would charge shareholders twice for the same obligation — worth **$4.04/share**, or most of the model's original gap to market.

There are exactly two internally consistent treatments:

| | Cash flows | WACC weights | Net debt |
|---|---|---|---|
| **Operating-lease treatment** (used here) | EBIT after rent | All-equity | Leases excluded |
| **Capitalized-lease treatment** | Add rent back to EBIT, depreciate the ROU asset | Lease liability as debt | Leases included |

Mixing them — expensing rent in the cash flows *and* treating leases as debt in the bridge — is a common error and the specific one this module exists to prevent. Flipping `equity_bridge.treat_leases_as_debt` in the config switches the bridge, so the alternative can be quantified rather than only described.

Under the operating-lease treatment CMG has **no financial debt at all**, so net debt is simply negative cash: **–$0.68B**. Enterprise value of $26.14B bridges to $26.82B of equity value, or $19.98 per diluted share.

**The comps side deliberately uses the opposite convention.** Peer EV/Revenue and EV/EBITDA multiples are quoted on a lease-*inclusive* enterprise value, because the data provider rolls lease liabilities into total debt for every company in the peer set. Applying those multiples to CMG therefore requires a lease-inclusive bridge to stay apples-to-apples. Using the DCF's bridge there would inflate the comps-implied price by measuring CMG on a different basis than the peers it is being compared to.

### Terminal value

Gordon growth (perpetuity growth) method, with a 3.0% terminal growth rate — roughly a long-run nominal GDP proxy, comfortably below the 9.49% WACC.

## Sensitivity: WACC vs. terminal growth

Implied share price across a range of WACC and terminal growth assumptions ([full table](outputs/tables/dcf_sensitivity.csv)):

| WACC \ g | 2.0% | 2.5% | 3.0% | 3.5% | 4.0% |
|---|---|---|---|---|---|
| 7.5% | $24.41 | $26.42 | $28.88 | $31.95 | $35.90 |
| 8.0% | $22.35 | $24.00 | $25.97 | $28.38 | $31.40 |
| 8.5% | $20.61 | $21.97 | $23.59 | $25.53 | $27.90 |
| **9.0%** | $19.12 | $20.27 | $21.61 | $23.19 | $25.10 |
| **9.5%** | $17.82 | $18.80 | **$19.93** | $21.25 | $22.81 |
| 10.0% | $16.69 | $17.53 | $18.50 | $19.60 | $20.90 |
| 10.5% | $15.70 | $16.43 | $17.25 | $18.20 | $19.28 |

At the most generous corner of this grid (7.5% WACC, 4.0% terminal growth), the DCF implies $35.90 — within about 3% of the $36.95 market price. So the market's valuation is reachable inside a defensible assumption set, but only at its edge: it requires a cost of equity roughly two points below the CAPM output *and* terminal growth a full point above long-run nominal GDP. At the base-case WACC of 9.49%, no terminal growth rate in this range gets there.

## Comparable companies

Peer set: Sweetgreen (SG), Shake Shack (SHAK), Wingstop (WING), Domino's (DPZ), Yum! Brands (YUM), CAVA Group (CAVA) — a mix of fast-casual pure-plays and larger franchisors, chosen for revenue-model similarity (restaurant/franchise economics) over CMG's exact growth profile.

| Ticker | EV/Revenue | EV/EBITDA | P/E | Revenue growth |
|---|---|---|---|---|
| SG | 1.51x | n/m (loss-making) | n/m (loss-making) | 3.8% |
| SHAK | 2.24x | 20.2x | 71.0x | 17.2% |
| WING | 5.72x | 17.6x | 25.8x | 6.4% |
| DPZ | 3.23x | 15.9x | 19.0x | 4.3% |
| YUM | 6.18x | 17.6x | 18.8x | 12.2% |
| CAVA | 5.23x | 44.7x | 107.4x | 31.3% |
| **CMG** | 4.15x | 22.6x | 34.2x | 9.3% |

Full detail (including implied share price by multiple) is in [`outputs/tables/comps_implied_valuation.csv`](outputs/tables/comps_implied_valuation.csv).

**Sweetgreen is screened out of the P/E statistics.** yfinance reports a positive ~77x "trailing" P/E for SG on *negative* GAAP EPS of –$1.14, which is a forward or normalized figure surfaced under a trailing field. A positive reported multiple is not evidence of positive earnings, so the peer filter tests net income and diluted EPS directly rather than trusting the multiple's sign. Leaving SG in pulled the peer P/E median from 25.8x up to 48.4x — nearly double — on the strength of a number that means nothing.

**P/E is still excluded from the headline comps range.** Even after that screen, CAVA's ~107x P/E (a hyper-growth outlier still scaling toward maturity) makes P/E a fragile cross-sectional comparison across a peer set this small. EV/Revenue and EV/EBITDA are capital-structure- and earnings-quality-agnostic and are used as the primary comps range instead:

**Comps-implied range: $9.85 – $75.54, median-multiple midpoint ≈ $31**

Worth noting: with the loss-maker screened out, the median P/E of 25.8x implies **$29.43/share** — squarely in line with the EV/EBITDA median of $27.60 and the EV/Revenue median of $34.03. The corrected P/E now corroborates the headline range instead of contradicting it, which is itself a check that the screen was the right call.

## Interpreting the gap to market price

Both methods still land below CMG's current $36.95 price at their base case/median, though less dramatically than an earlier version of this model implied — see the [lease decision](#the-lease-decision-and-why-the-bridge-is-consistent-with-it) for why. That's not a bug — it's a legitimate, common outcome when valuing a stock the market has historically rewarded with a premium multiple (CMG's own EV/EBITDA of 22.6x is above every peer except CAVA). A few honest explanations for the gap, none of which this model tries to capture:

- The market may be pricing in a longer runway of double-digit growth than this model's fading growth path assumes (e.g. continued strong new-unit economics, further international expansion, Chipotlanes, digital/loyalty flywheel effects).
- A lower risk-free-rate or ERP assumption, or a re-rating of CMG's beta, would raise the DCF's valuation — the sensitivity table above shows how much.
- Comps-based valuation is sensitive to which peers are included; a peer set weighted more toward high-growth names (like CAVA) rather than mature franchisors (like YUM, DPZ) would imply a higher range.

## Limitations

- **Single-scenario base case.** No explicit bull/bear case beyond the WACC × terminal growth sensitivity grid. Revenue growth, margins, and reinvestment are all held at one path; only the discount rate and terminal growth are flexed.
- **yfinance data quality.** Some fields (e.g. beta, EBITDA) are yfinance's own derived figures rather than pulled directly from filings, and can differ from other data providers.
- **Small comp set.** Six peers is enough for a directional range, not a statistically robust sample — P/E in particular is easily skewed by one or two names (see above).
- **Terminal reinvestment is not normalized.** CapEx stays at 5.0% of revenue against 3.0% D&A in the terminal year, so the perpetuity has CMG reinvesting at ~1.7x depreciation forever while growing only 3%. That is conservative by construction and is a meaningful part of why the DCF sits below market. Tying terminal reinvestment to growth and returns on capital would be the more standard treatment.
- **Share count mixes vintages.** The bridge divides by last fiscal year's *average* diluted shares while the market comparison uses today's price. Those differ by roughly 6% given CMG's buyback pace.
- **The lease-as-debt alternative is a config toggle, not a fully modeled scenario.** Flipping `treat_leases_as_debt` changes the bridge but does not add rent back to EBIT or depreciate the right-of-use asset, so it shows the direction of that treatment rather than a complete implementation of it.
