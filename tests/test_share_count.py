"""The share count used in the bridge has to match the price it is compared to."""

import pytest

from src.data.fetch import CompanySnapshot


def _cmg(**overrides) -> CompanySnapshot:
    defaults = dict(
        ticker="CMG", name="Chipotle Mexican Grill, Inc.", price=36.95,
        shares_diluted=1_342_616_000.0, market_cap=46_757_195_776.0,
        total_debt=5_419_195_904.0, cash=677_857_024.0, beta=0.937,
        revenue=11_925_601_000.0, ebitda=2_374_190_000.0,
        operating_income=2_012_808_000.0, net_income=1_535_761_000.0,
        diluted_eps=1.14, ev_to_ebitda=22.642, ev_to_revenue=4.146,
        trailing_pe=34.212963, revenue_growth=0.093,
    )
    defaults.update(overrides)
    return CompanySnapshot(**defaults)


def test_current_share_count_comes_from_market_cap_and_price():
    t = _cmg()
    assert t.shares_outstanding_current == pytest.approx(46_757_195_776.0 / 36.95)


def test_fiscal_year_average_is_materially_staler_than_current():
    """CMG buys back stock, so last year's average count is ~6% too high."""
    t = _cmg()
    overstatement = t.shares_diluted / t.shares_outstanding_current - 1
    assert overstatement == pytest.approx(0.061, abs=0.005)


def test_stale_share_count_understates_value_per_share():
    t = _cmg()
    equity_value = 26_820_000_000.0
    assert equity_value / t.shares_outstanding_current > equity_value / t.shares_diluted


def test_falls_back_to_reported_diluted_when_price_is_missing():
    t = _cmg(price=0.0)
    assert t.shares_outstanding_current == t.shares_diluted


def test_falls_back_when_market_cap_is_missing():
    t = _cmg(market_cap=0.0)
    assert t.shares_outstanding_current == t.shares_diluted
