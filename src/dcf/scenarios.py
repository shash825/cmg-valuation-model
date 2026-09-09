"""Runs the DCF under bull, base, and bear operating assumptions.

The WACC x terminal-growth grid in sensitivity.py flexes the *discount rate*:
it asks what the same forecast is worth to investors with different required
returns. These scenarios flex the *business*: different revenue paths, margins,
and terminal growth. Both matter, and neither answers the other's question --
no grid of discount rates tells you what CMG is worth if comparable sales turn
negative.

Each scenario overrides only the assumption keys it declares; everything else
falls through to the shared dcf: block, so the cases stay honest about what
actually differs between them.
"""

from __future__ import annotations

import copy

import pandas as pd

from src.dcf.equity_bridge import implied_share_price
from src.dcf.projections import build_fcf_projection
from src.dcf.terminal_value import (
    enterprise_value,
    gordon_growth_terminal_value,
    reinvestment_terminal_value,
    terminal_diagnostics,
)

OVERRIDABLE = (
    "revenue_growth",
    "operating_margin",
    "capex_pct_revenue",
    "da_pct_revenue",
    "nwc_pct_revenue_change",
    "tax_rate",
    "terminal_growth_rate",
    "terminal_return_on_capital",
)


def apply_scenario(assumptions: dict, overrides: dict) -> dict:
    """Returns a copy of `assumptions` with the scenario's overrides applied.

    Deep-copied so scenarios cannot leak into one another, and restricted to a
    known key list so a typo in the config surfaces as an error rather than
    silently doing nothing.
    """
    scoped = {k: v for k, v in overrides.items() if k != "label"}
    unknown = set(scoped) - set(OVERRIDABLE)
    if unknown:
        raise ValueError(
            f"Scenario declares unknown assumption key(s): {sorted(unknown)}. "
            f"Overridable keys are: {sorted(OVERRIDABLE)}"
        )

    merged = copy.deepcopy(assumptions)
    merged["dcf"].update(scoped)
    return merged


def _terminal_value(projection: pd.DataFrame, assumptions: dict, wacc: float) -> float:
    dcf = assumptions["dcf"]
    g = dcf["terminal_growth_rate"]

    if dcf.get("terminal_method", "gordon_growth") == "reinvestment_rate":
        return reinvestment_terminal_value(
            terminal_nopat=float(projection["nopat"].iloc[-1]),
            wacc=wacc,
            terminal_growth=g,
            return_on_capital=dcf["terminal_return_on_capital"],
        )

    return gordon_growth_terminal_value(float(projection["unlevered_fcf"].iloc[-1]), wacc, g)


def run_scenario(
    assumptions: dict,
    base_revenue: float,
    base_year: int,
    wacc: float,
    net_debt: float,
    shares: float,
) -> dict:
    """Full DCF for one already-merged assumption set."""
    projection = build_fcf_projection(base_revenue, base_year, assumptions)
    fcfs = projection["unlevered_fcf"].tolist()

    tv = _terminal_value(projection, assumptions, wacc)
    ev = enterprise_value(fcfs, tv, wacc)["enterprise_value"]
    last = projection.iloc[-1]

    diagnostics = terminal_diagnostics(
        nopat=float(last["nopat"]),
        capex=float(last["capex"]),
        da=float(last["da"]),
        nwc_change=float(last["nwc_change"]),
        terminal_growth=assumptions["dcf"]["terminal_growth_rate"],
    )

    return {
        "exit_revenue": float(last["revenue"]),
        "exit_operating_margin": float(last["operating_margin"]),
        "terminal_growth": assumptions["dcf"]["terminal_growth_rate"],
        "enterprise_value": ev,
        "implied_share_price": implied_share_price(ev, net_debt, shares),
        "implied_terminal_roic": diagnostics["implied_return_on_capital"],
    }


def run_all_scenarios(
    assumptions: dict,
    base_revenue: float,
    base_year: int,
    wacc: float,
    net_debt: float,
    shares: float,
    current_price: float,
) -> pd.DataFrame:
    """One row per scenario, ordered bear -> base -> bull."""
    rows = []
    for name in ("bear", "base", "bull"):
        overrides = assumptions.get("scenarios", {}).get(name) or {}
        merged = apply_scenario(assumptions, overrides)
        result = run_scenario(merged, base_revenue, base_year, wacc, net_debt, shares)

        price = result["implied_share_price"]
        rows.append(
            {
                "scenario": name,
                "label": overrides.get("label", name),
                "exit_revenue_bn": result["exit_revenue"] / 1e9,
                "exit_operating_margin": result["exit_operating_margin"],
                "terminal_growth": result["terminal_growth"],
                "implied_terminal_roic": result["implied_terminal_roic"],
                "implied_share_price": price,
                "upside_vs_market": price / current_price - 1.0,
            }
        )

    return pd.DataFrame(rows).set_index("scenario")
