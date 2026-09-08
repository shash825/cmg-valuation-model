"""Cost of capital.

CMG carries no traditional bonds or bank debt -- its only "debt" on the
balance sheet is capitalized operating lease liabilities (all restaurants are
leased), which are already expensed above the operating-income line. We treat
the company as effectively all-equity-funded and set WACC equal to the cost
of equity via CAPM, rather than blending in lease liabilities as if they were
financial debt. See README methodology section for the alternative
(lease-as-debt) treatment considered and why it was set aside.
"""

from __future__ import annotations


def cost_of_equity(risk_free_rate: float, beta: float, equity_risk_premium: float) -> float:
    """CAPM: Re = Rf + Beta * ERP."""
    return risk_free_rate + beta * equity_risk_premium


def compute_wacc(risk_free_rate: float, beta: float, equity_risk_premium: float) -> float:
    """WACC == cost of equity under the all-equity-funded treatment used here."""
    return cost_of_equity(risk_free_rate, beta, equity_risk_premium)
