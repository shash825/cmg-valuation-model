"""Terminal value, plus the diagnostics needed to sanity-check it.

Terminal value is most of this DCF, so the assumption embedded in it deserves
to be visible rather than implied. Two methods are available:

  * `gordon_growth_terminal_value` grows the final projected FCF in perpetuity.
    Simple, and the default, but it inherits whatever reinvestment the final
    forecast year happened to assume.
  * `reinvestment_terminal_value` derives the perpetuity from a return on
    capital instead: a firm growing at g while earning ROIC must reinvest
    g / ROIC of its after-tax operating profit to fund that growth.

`terminal_diagnostics` makes the two comparable by backing the implied return
on capital out of the default method, which is the check worth running before
trusting either number. A headline like "capex is 1.7x depreciation forever"
sounds aggressive but says little on its own: what matters is net reinvestment
as a share of NOPAT, and the return that reinvestment implies.
"""

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


def reinvestment_terminal_value(
    terminal_nopat: float,
    wacc: float,
    terminal_growth: float,
    return_on_capital: float,
) -> float:
    """Terminal value from a return-on-capital assumption rather than a raw FCF.

    A firm growing at g while earning ROIC on new capital must plough back
    g / ROIC of its NOPAT to fund that growth. What is left is distributable:

        TV = NOPAT * (1 + g) * (1 - g / ROIC) / (WACC - g)

    This makes the growth/return trade-off explicit. Growth is only worth
    anything when ROIC exceeds WACC; below that, growing faster destroys value,
    and this formula shows it while the Gordon growth version hides it.
    """
    if wacc <= terminal_growth:
        raise ValueError("WACC must exceed the terminal growth rate for the perpetuity to converge.")
    if return_on_capital <= 0:
        raise ValueError("Return on capital must be positive.")
    if return_on_capital <= terminal_growth:
        raise ValueError(
            "Return on capital must exceed the terminal growth rate; otherwise the "
            "implied reinvestment rate is 100% or more and there is no free cash flow."
        )

    reinvestment_rate = terminal_growth / return_on_capital
    distributable = terminal_nopat * (1 + terminal_growth) * (1 - reinvestment_rate)
    return distributable / (wacc - terminal_growth)


def terminal_diagnostics(
    nopat: float,
    capex: float,
    da: float,
    nwc_change: float,
    terminal_growth: float,
) -> dict:
    """Backs the implied return on capital out of the terminal year's cash flow.

    Net reinvestment is capex less depreciation plus the working capital build --
    the capital genuinely being added to the business, not the portion merely
    replacing what wore out. Expressed as a share of NOPAT and set against the
    terminal growth rate, it implies the return the model is assuming on that
    new capital:

        implied ROIC = terminal growth / reinvestment rate

    If that number comes back implausible for the business, the terminal value
    is not defensible no matter how reasonable WACC and g look on their own.
    """
    net_reinvestment = capex - da + nwc_change
    reinvestment_rate = net_reinvestment / nopat if nopat else float("nan")
    implied_roic = terminal_growth / reinvestment_rate if reinvestment_rate else float("inf")

    return {
        "net_reinvestment": net_reinvestment,
        "capex_to_da": capex / da if da else float("inf"),
        "reinvestment_rate": reinvestment_rate,
        "implied_return_on_capital": implied_roic,
    }
