"""WACC x terminal growth sensitivity table for implied share price."""

from __future__ import annotations

import pandas as pd

from src.dcf.terminal_value import enterprise_value, gordon_growth_terminal_value


def implied_share_price(
    unlevered_fcfs: list[float],
    wacc: float,
    terminal_growth: float,
    net_debt: float,
    shares_diluted: float,
) -> float:
    tv = gordon_growth_terminal_value(unlevered_fcfs[-1], wacc, terminal_growth)
    ev = enterprise_value(unlevered_fcfs, tv, wacc)["enterprise_value"]
    equity_value = ev - net_debt
    return equity_value / shares_diluted


def sensitivity_table(
    unlevered_fcfs: list[float],
    wacc_range: list[float],
    terminal_growth_range: list[float],
    net_debt: float,
    shares_diluted: float,
) -> pd.DataFrame:
    """Rows = WACC, columns = terminal growth rate. Cells = implied share price."""
    table = {}
    for tg in terminal_growth_range:
        col = []
        for wacc in wacc_range:
            if wacc <= tg:
                col.append(None)
                continue
            col.append(implied_share_price(unlevered_fcfs, wacc, tg, net_debt, shares_diluted))
        table[f"{tg:.1%}"] = col

    df = pd.DataFrame(table, index=[f"{w:.1%}" for w in wacc_range])
    df.index.name = "WACC \\ Terminal Growth"
    return df
