"""Bridges enterprise value to equity value, and makes the lease decision explicit.

The lease question is the one modeling choice here that materially moves the
answer, so it gets its own module rather than a bare subtraction inside main().

CMG leases nearly every restaurant. Under ASC 842 those leases sit on the
balance sheet as a ~$5.4B liability, and yfinance rolls that into `totalDebt`.
But rent expense is *already* deducted above the operating-income line, so the
economic cost of those leases is already inside the unlevered free cash flow
this model discounts. Subtracting the lease liability again in the EV -> equity
bridge would charge shareholders for the same obligation twice.

So the two internally consistent treatments are:

  1. Operating-lease treatment (used here). Leave EBIT after rent, leave leases
     out of the WACC weights, and leave the lease liability out of net debt.
  2. Capitalized-lease treatment. Add rent back to EBIT, add the lease
     liability to both the WACC weights and net debt, and depreciate the
     right-of-use asset.

The model uses (1) throughout, which matches the all-equity WACC in wacc.py.
Doing (1) for the cash flows and (2) for the bridge -- the mistake this module
exists to prevent -- understates equity value by the full lease liability.

Note the comps side deliberately does NOT use this bridge: peer EV/Revenue and
EV/EBITDA multiples are quoted on a lease-inclusive enterprise value, so
applying them to CMG requires a lease-inclusive bridge for comparability.
See src/comps/implied_valuation.py.
"""

from __future__ import annotations


def net_debt(
    total_debt: float,
    cash: float,
    treat_leases_as_debt: bool,
    lease_share_of_total_debt: float,
) -> float:
    """Net debt for the DCF's EV -> equity bridge.

    `lease_share_of_total_debt` is the fraction of reported total debt that is
    capitalized operating leases rather than bonds or bank borrowings. For CMG
    that is 1.0: the company has no traditional financial debt outstanding.
    """
    if not 0.0 <= lease_share_of_total_debt <= 1.0:
        raise ValueError("lease_share_of_total_debt must be between 0 and 1.")

    debt_in_bridge = total_debt if treat_leases_as_debt else total_debt * (1.0 - lease_share_of_total_debt)
    return debt_in_bridge - cash


def equity_value(enterprise_value: float, net_debt_amount: float) -> float:
    return enterprise_value - net_debt_amount


def implied_share_price(enterprise_value: float, net_debt_amount: float, shares_diluted: float) -> float:
    if shares_diluted <= 0:
        raise ValueError("Diluted share count must be positive.")
    return equity_value(enterprise_value, net_debt_amount) / shares_diluted
