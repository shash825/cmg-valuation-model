"""Applies peer trading multiples to CMG's own financials to imply a valuation range.

Note the net debt convention here is deliberately different from the DCF's.
The DCF discounts cash flows that are already after rent expense, so it leaves
the capitalized lease liability out of its bridge (see src/dcf/equity_bridge.py).
Peer EV/Revenue and EV/EBITDA multiples, by contrast, are quoted on a
lease-INCLUSIVE enterprise value, because the data provider rolls lease
liabilities into total debt for every company in the peer set. Applying those
multiples to CMG therefore requires a lease-inclusive bridge to stay
apples-to-apples. Using the DCF's lease-excluded bridge here would inflate the
comps-implied price by systematically understating CMG's claims relative to how
the peers themselves are being measured.
"""

from __future__ import annotations

import pandas as pd

from src.data.fetch import CompanySnapshot


def implied_valuation_from_comps(target: CompanySnapshot, peer_stats: pd.DataFrame) -> pd.DataFrame:
    """For each multiple (EV/Revenue, EV/EBITDA, P/E), applies the peer median,
    min, and max to CMG's own revenue/EBITDA/EPS to get an implied share price.
    """
    # Lease-inclusive on purpose -- see the module docstring.
    net_debt = target.total_debt - target.cash
    rows = []

    for stat in ["min", "median", "max"]:
        ev_rev_mult = peer_stats.loc[stat, "ev_to_revenue"]
        implied_ev = ev_rev_mult * target.revenue
        implied_equity = implied_ev - net_debt
        rows.append(
            {
                "multiple": "EV/Revenue",
                "stat": stat,
                "multiple_value": ev_rev_mult,
                "implied_share_price": implied_equity / target.shares_outstanding_current,
            }
        )

        ev_ebitda_mult = peer_stats.loc[stat, "ev_to_ebitda"]
        if pd.notna(ev_ebitda_mult):
            implied_ev = ev_ebitda_mult * target.ebitda
            implied_equity = implied_ev - net_debt
            rows.append(
                {
                    "multiple": "EV/EBITDA",
                    "stat": stat,
                    "multiple_value": ev_ebitda_mult,
                    "implied_share_price": implied_equity / target.shares_outstanding_current,
                }
            )

        pe_mult = peer_stats.loc[stat, "trailing_pe"]
        if pd.notna(pe_mult):
            rows.append(
                {
                    "multiple": "P/E",
                    "stat": stat,
                    "multiple_value": pe_mult,
                    "implied_share_price": pe_mult * target.diluted_eps,
                }
            )

    return pd.DataFrame(rows)
