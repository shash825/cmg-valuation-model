"""Builds the comparable companies multiples table."""

from __future__ import annotations

import pandas as pd

from src.data.fetch import CompanySnapshot


def build_comps_table(peers: list[CompanySnapshot]) -> pd.DataFrame:
    rows = []
    for p in peers:
        rows.append(
            {
                "ticker": p.ticker,
                "name": p.name,
                "market_cap": p.market_cap,
                "revenue_growth": p.revenue_growth,
                "ev_to_revenue": p.ev_to_revenue,
                # A loss-making EBITDA (or negative multiple) isn't a meaningful
                # trading comp -- exclude it from the multiple rather than let one
                # distressed value skew the peer median.
                "ev_to_ebitda": p.ev_to_ebitda if p.ev_to_ebitda and p.ev_to_ebitda > 0 else None,
                "trailing_pe": p.trailing_pe if p.trailing_pe and p.trailing_pe > 0 else None,
            }
        )
    df = pd.DataFrame(rows).set_index("ticker")
    return df


def peer_summary_stats(comps_df: pd.DataFrame) -> pd.DataFrame:
    stats = comps_df[["ev_to_revenue", "ev_to_ebitda", "trailing_pe"]].agg(["median", "mean", "min", "max"])
    return stats
