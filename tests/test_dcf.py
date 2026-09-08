"""Sanity checks on the DCF math -- not exhaustive, just catches silent breakage."""

import pytest

from src.dcf.equity_bridge import implied_share_price, net_debt
from src.dcf.projections import build_fcf_projection
from src.dcf.terminal_value import discount_to_present, enterprise_value, gordon_growth_terminal_value
from src.dcf.wacc import compute_wacc, cost_of_equity


def _sample_assumptions():
    return {
        "dcf": {
            "projection_years": 5,
            "revenue_growth": [0.10, 0.10, 0.08, 0.08, 0.06],
            "operating_margin": [0.16, 0.16, 0.17, 0.17, 0.17],
            "capex_pct_revenue": [0.05, 0.05, 0.05, 0.05, 0.05],
            "da_pct_revenue": [0.03, 0.03, 0.03, 0.03, 0.03],
            "nwc_pct_revenue_change": [0.003, 0.003, 0.003, 0.003, 0.003],
            "tax_rate": 0.25,
        }
    }


def test_cost_of_equity_capm():
    assert cost_of_equity(risk_free_rate=0.04, beta=1.0, equity_risk_premium=0.05) == pytest.approx(0.09)


def test_wacc_equals_cost_of_equity():
    wacc = compute_wacc(risk_free_rate=0.048, beta=0.94, equity_risk_premium=0.05)
    assert wacc == pytest.approx(0.048 + 0.94 * 0.05)


def test_revenue_projection_compounds_correctly():
    df = build_fcf_projection(base_revenue=1000.0, base_year=2025, assumptions=_sample_assumptions())
    assert df.loc[2026, "revenue"] == pytest.approx(1100.0)
    assert df.loc[2027, "revenue"] == pytest.approx(1100.0 * 1.10)


def test_fcf_projection_has_five_years():
    df = build_fcf_projection(base_revenue=1000.0, base_year=2025, assumptions=_sample_assumptions())
    assert len(df) == 5
    assert list(df.index) == [2026, 2027, 2028, 2029, 2030]


def test_terminal_value_requires_wacc_above_growth():
    with pytest.raises(ValueError):
        gordon_growth_terminal_value(final_year_fcf=100.0, wacc=0.03, terminal_growth=0.03)


def test_terminal_value_grows_with_lower_wacc():
    tv_high_wacc = gordon_growth_terminal_value(100.0, wacc=0.10, terminal_growth=0.03)
    tv_low_wacc = gordon_growth_terminal_value(100.0, wacc=0.08, terminal_growth=0.03)
    assert tv_low_wacc > tv_high_wacc


def test_discount_to_present_reduces_future_cash_flows():
    pv = discount_to_present([100.0, 100.0], wacc=0.10)
    assert pv[0] < 100.0
    assert pv[1] < pv[0]


def test_enterprise_value_sums_pv_components():
    result = enterprise_value(unlevered_fcfs=[100.0, 110.0], terminal_value=2000.0, wacc=0.10)
    assert result["enterprise_value"] == pytest.approx(result["sum_pv_fcfs"] + result["pv_terminal_value"])


def test_nwc_scales_with_revenue_change_not_revenue_level():
    """Working capital is a stock; only its movement is a cash flow.

    Base revenue 1000 growing 10% means revenue rises by 100 in year 1, so at
    2% of the change the working capital drag is 2.0, not 2% of the 1100 level.
    """
    assumptions = _sample_assumptions()
    assumptions["dcf"]["nwc_pct_revenue_change"] = [0.02] * 5
    df = build_fcf_projection(base_revenue=1000.0, base_year=2025, assumptions=assumptions)

    assert df.loc[2026, "revenue_change"] == pytest.approx(100.0)
    assert df.loc[2026, "nwc_change"] == pytest.approx(2.0)
    assert df.loc[2026, "nwc_change"] != pytest.approx(0.02 * df.loc[2026, "revenue"])


def test_leases_stay_out_of_the_dcf_bridge_by_default():
    """Rent is already expensed above EBIT, so the lease liability is not net debt."""
    nd = net_debt(
        total_debt=5_419_195_904,
        cash=677_857_024,
        treat_leases_as_debt=False,
        lease_share_of_total_debt=1.0,
    )
    assert nd == pytest.approx(-677_857_024)


def test_capitalized_lease_treatment_restores_the_liability():
    nd = net_debt(
        total_debt=5_419_195_904,
        cash=677_857_024,
        treat_leases_as_debt=True,
        lease_share_of_total_debt=1.0,
    )
    assert nd == pytest.approx(5_419_195_904 - 677_857_024)


def test_double_counting_leases_costs_the_full_liability_per_share():
    """The two treatments differ by exactly the lease liability per share."""
    shares = 1_342_616_000.0
    ev = 25_000_000_000.0
    kwargs = dict(total_debt=5_419_195_904, cash=677_857_024, lease_share_of_total_debt=1.0)

    correct = implied_share_price(ev, net_debt(treat_leases_as_debt=False, **kwargs), shares)
    double_counted = implied_share_price(ev, net_debt(treat_leases_as_debt=True, **kwargs), shares)

    assert correct - double_counted == pytest.approx(5_419_195_904 / shares)


def test_lease_share_must_be_a_fraction():
    with pytest.raises(ValueError):
        net_debt(total_debt=100.0, cash=0.0, treat_leases_as_debt=False, lease_share_of_total_debt=1.5)


def test_implied_share_price_rejects_zero_share_count():
    with pytest.raises(ValueError):
        implied_share_price(enterprise_value=1000.0, net_debt_amount=0.0, shares_diluted=0.0)
