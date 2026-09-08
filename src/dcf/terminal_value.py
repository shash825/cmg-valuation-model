"""Terminal value via the Gordon growth (perpetuity growth) method."""

from __future__ import annotations


def gordon_growth_terminal_value(final_year_fcf: float, wacc: float, terminal_growth: float) -> float:
    if wacc <= terminal_growth:
        raise ValueError("WACC must exceed the terminal growth rate for the perpetuity to converge.")
    return final_year_fcf * (1 + terminal_growth) / (wacc - terminal_growth)


def discount_to_present(cash_flows: list[float], wacc: float) -> list[float]:
    """Discounts a list of cash flows (year 1, year 2, ...) back to present value."""
    return [cf / (1 + wacc) ** (i + 1) for i, cf in enumerate(cash_flows)]


def enterprise_value(unlevered_fcfs: list[float], terminal_value: float, wacc: float) -> dict:
    """Sums discounted explicit-period FCFs and the discounted terminal value."""
    n = len(unlevered_fcfs)
    pv_fcfs = discount_to_present(unlevered_fcfs, wacc)
    pv_terminal = terminal_value / (1 + wacc) ** n
    return {
        "pv_fcfs": pv_fcfs,
        "sum_pv_fcfs": sum(pv_fcfs),
        "pv_terminal_value": pv_terminal,
        "enterprise_value": sum(pv_fcfs) + pv_terminal,
    }
