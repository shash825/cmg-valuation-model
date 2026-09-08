"""Checks on the comparable-companies logic, especially which peers qualify."""

import pandas as pd
import pytest

from src.comps.peer_data import build_comps_table, peer_summary_stats
from src.data.fetch import CompanySnapshot


def _snapshot(ticker: str, **overrides) -> CompanySnapshot:
    defaults = dict(
        ticker=ticker,
        name=ticker,
        price=10.0,
        shares_diluted=100.0,
        market_cap=1000.0,
        total_debt=100.0,
        cash=50.0,
        beta=1.0,
        revenue=500.0,
        ebitda=100.0,
        operating_income=80.0,
        net_income=60.0,
        diluted_eps=0.6,
        ev_to_ebitda=10.0,
        ev_to_revenue=2.0,
        trailing_pe=16.0,
        revenue_growth=0.05,
    )
    defaults.update(overrides)
    return CompanySnapshot(**defaults)


def test_loss_maker_is_excluded_from_pe_even_with_a_positive_reported_multiple():
    """Sweetgreen's case: negative GAAP EPS but a positive reported trailing P/E.

    A positive multiple is not evidence of positive earnings, so the filter has
    to look at the earnings themselves.
    """
    loss_maker = _snapshot("SG", net_income=-134_065_000.0, diluted_eps=-1.14, trailing_pe=77.2, ev_to_ebitda=-17.3)
    df = build_comps_table([loss_maker])

    assert pd.isna(df.loc["SG", "trailing_pe"])
    assert pd.isna(df.loc["SG", "ev_to_ebitda"])
    assert df.loc["SG", "ev_to_revenue"] == pytest.approx(2.0)


def test_profitable_peer_keeps_its_pe():
    df = build_comps_table([_snapshot("DPZ", net_income=500.0, diluted_eps=5.0, trailing_pe=19.0)])
    assert df.loc["DPZ", "trailing_pe"] == pytest.approx(19.0)


def test_loss_maker_does_not_move_the_peer_pe_median():
    profitable = [
        _snapshot("A", trailing_pe=18.0),
        _snapshot("B", trailing_pe=20.0),
        _snapshot("C", trailing_pe=26.0),
    ]
    loss_maker = _snapshot("D", net_income=-10.0, diluted_eps=-0.1, trailing_pe=77.0)

    without = peer_summary_stats(build_comps_table(profitable))
    with_loss_maker = peer_summary_stats(build_comps_table(profitable + [loss_maker]))

    assert without.loc["median", "trailing_pe"] == pytest.approx(20.0)
    assert with_loss_maker.loc["median", "trailing_pe"] == pytest.approx(20.0)
    assert with_loss_maker.loc["max", "trailing_pe"] == pytest.approx(26.0)


def test_ev_to_revenue_survives_for_loss_makers():
    """EV/Revenue is the multiple that still means something for a loss-maker."""
    stats = peer_summary_stats(build_comps_table([_snapshot("SG", net_income=-10.0, diluted_eps=-0.1, ev_to_revenue=1.51)]))
    assert stats.loc["median", "ev_to_revenue"] == pytest.approx(1.51)
