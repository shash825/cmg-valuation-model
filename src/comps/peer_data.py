"""Builds the comparable companies multiples table."""

from __future__ import annotations

import pandas as pd

from src.data.fetch import CompanySnapshot


def _meaningful_pe(p: CompanySnapshot) -> float | None:
    """Trailing P/E, but only where the company actually earns money.

    A positive reported P/E is not sufficient evidence of positive earnings.
    Data providers sometimes surface a forward or normalized figure under the
    trailing field, which is how Sweetgreen shows a ~77x "trailing" P/E on
    negative GAAP EPS. Requiring positive net income and positive diluted EPS
    keeps loss-makers out of the peer median instead of letting a meaningless
    multiple set the range.
    """
    if p.trailing_pe is None or p.trailing_pe <= 0:
        return None
    if p.net_income <= 0 or p.diluted_eps <= 0:
        return None
    return p.trailing_pe


def build_comps_table(peers: list[CompanySnapshot]) -> pd.DataFrame:
    rows = []
    for p in peers:
        rows.append(
            {
                "ticker": p.ticker,
                "name": p.name,
                "market_cap": p.market_cap,
                "revenue_growth": p.revenue_growth,
                "net_income": p.net_income,
                "ev_to_revenue": p.ev_to_revenue,
                # A loss-making EBITDA (or negative multiple) isn't a meaningful
                # trading comp -- exclude it from the multiple rather than let one
                # distressed value skew the peer median.
                "ev_to_ebitda": p.ev_to_ebitda if p.ev_to_ebitda and p.ev_to_ebitda > 0 else None,
                "trailing_pe": _meaningful_pe(p),
            }
        )
    df = pd.DataFrame(rows).set_index("ticker")
    return df


def peer_summary_stats(comps_df: pd.DataFrame) -> pd.DataFrame:
    stats = comps_df[["ev_to_revenue", "ev_to_ebitda", "trailing_pe"]].agg(["median", "mean", "min", "max"])
    return stats
