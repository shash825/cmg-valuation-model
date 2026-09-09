"""Checks on the scenario engine and the terminal-value diagnostics."""

import copy

import pytest
import yaml

from src.dcf.scenarios import apply_scenario, run_all_scenarios
from src.dcf.terminal_value import reinvestment_terminal_value, terminal_diagnostics


def _assumptions():
    with open("config/assumptions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_scenario_overrides_only_declared_keys():
    base = _assumptions()
    merged = apply_scenario(base, {"terminal_growth_rate": 0.01, "label": "test"})

    assert merged["dcf"]["terminal_growth_rate"] == 0.01
    # Everything not declared falls through unchanged.
    assert merged["dcf"]["revenue_growth"] == base["dcf"]["revenue_growth"]
    assert merged["dcf"]["tax_rate"] == base["dcf"]["tax_rate"]


def test_scenario_does_not_mutate_the_shared_assumptions():
    """Scenarios run in sequence, so a leak would silently corrupt later cases."""
    base = _assumptions()
    snapshot = copy.deepcopy(base)

    apply_scenario(base, {"revenue_growth": [0.5] * 5})

    assert base == snapshot


def test_unknown_scenario_key_is_rejected():
    """A typo in the config should fail loudly, not silently do nothing."""
    with pytest.raises(ValueError, match="unknown assumption key"):
        apply_scenario(_assumptions(), {"revenue_growht": [0.1] * 5})


def test_scenarios_are_ordered_and_monotonic():
    """Bear < base < bull. If that inverts, an assumption has the wrong sign."""
    df = run_all_scenarios(
        _assumptions(),
        base_revenue=11_925_601_000.0,
        base_year=2025,
        wacc=0.0949,
        net_debt=-677_857_024.0,
        shares=1_265_350_000.0,
        current_price=36.95,
    )

    assert list(df.index) == ["bear", "base", "bull"]
    prices = df["implied_share_price"].tolist()
    assert prices[0] < prices[1] < prices[2]


def test_upside_column_is_relative_to_the_market_price():
    df = run_all_scenarios(
        _assumptions(),
        base_revenue=11_925_601_000.0,
        base_year=2025,
        wacc=0.0949,
        net_debt=-677_857_024.0,
        shares=1_265_350_000.0,
        current_price=36.95,
    )
    row = df.loc["base"]
    assert row["upside_vs_market"] == pytest.approx(row["implied_share_price"] / 36.95 - 1)


def test_terminal_diagnostics_backs_out_the_implied_return():
    """A 16.2% reinvestment rate funding 3% growth implies ~18.5% ROIC."""
    d = terminal_diagnostics(
        nopat=2_368_260_000.0,
        capex=902_193_000.0,
        da=541_316_000.0,
        nwc_change=23_609_000.0,
        terminal_growth=0.03,
    )

    assert d["capex_to_da"] == pytest.approx(1.667, abs=0.01)
    assert d["reinvestment_rate"] == pytest.approx(0.162, abs=0.005)
    assert d["implied_return_on_capital"] == pytest.approx(0.185, abs=0.005)


def test_capex_above_da_does_not_by_itself_mean_heavy_reinvestment():
    """The headline ratio and the economically meaningful rate can disagree.

    Capex at 1.67x depreciation reads as aggressive, but net of depreciation it
    is only ~16% of NOPAT. Judging terminal value off the raw ratio would flag a
    problem that isn't there, which is why the diagnostic reports both.
    """
    d = terminal_diagnostics(
        nopat=2_368_260_000.0,
        capex=902_193_000.0,
        da=541_316_000.0,
        nwc_change=23_609_000.0,
        terminal_growth=0.03,
    )
    assert d["capex_to_da"] > 1.5
    assert d["reinvestment_rate"] < 0.20


def test_reinvestment_terminal_value_matches_the_formula():
    tv = reinvestment_terminal_value(
        terminal_nopat=1000.0, wacc=0.10, terminal_growth=0.03, return_on_capital=0.15
    )
    expected = 1000.0 * 1.03 * (1 - 0.03 / 0.15) / (0.10 - 0.03)
    assert tv == pytest.approx(expected)


def test_reinvestment_method_rejects_returns_below_growth():
    """ROIC <= g means reinvestment consumes everything; there is no perpetuity."""
    with pytest.raises(ValueError, match="Return on capital must exceed"):
        reinvestment_terminal_value(
            terminal_nopat=1000.0, wacc=0.10, terminal_growth=0.03, return_on_capital=0.03
        )


def test_growth_is_worth_less_when_returns_are_lower():
    """Same growth, lower ROIC, more capital consumed to fund it, less value."""
    high = reinvestment_terminal_value(1000.0, wacc=0.10, terminal_growth=0.03, return_on_capital=0.25)
    low = reinvestment_terminal_value(1000.0, wacc=0.10, terminal_growth=0.03, return_on_capital=0.12)
    assert high > low
