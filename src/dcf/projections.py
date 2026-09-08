"""Builds the 5-year revenue, margin, and free cash flow projection."""

from __future__ import annotations

import pandas as pd


def build_fcf_projection(base_revenue: float, base_year: int, assumptions: dict) -> pd.DataFrame:
    """Projects revenue -> EBIT -> unlevered free cash flow for each forecast year.

    FCF = EBIT * (1 - tax) + D&A - CapEx - increase in net working capital
    """
    dcf = assumptions["dcf"]
    years = [base_year + i + 1 for i in range(dcf["projection_years"])]

    revenues = []
    revenue = base_revenue
    for g in dcf["revenue_growth"]:
        revenue = revenue * (1 + g)
        revenues.append(revenue)

    df = pd.DataFrame(
        {
            "year": years,
            "revenue_growth": dcf["revenue_growth"],
            "revenue": revenues,
            "operating_margin": dcf["operating_margin"],
            "capex_pct_revenue": dcf["capex_pct_revenue"],
            "da_pct_revenue": dcf["da_pct_revenue"],
            "nwc_pct_revenue_change": dcf["nwc_pct_revenue_change"],
        }
    ).set_index("year")

    df["ebit"] = df["revenue"] * df["operating_margin"]
    df["tax_on_ebit"] = df["ebit"] * dcf["tax_rate"]
    df["nopat"] = df["ebit"] - df["tax_on_ebit"]
    df["da"] = df["revenue"] * df["da_pct_revenue"]
    df["capex"] = df["revenue"] * df["capex_pct_revenue"]
    df["nwc_change"] = df["revenue"] * df["nwc_pct_revenue_change"]
    df["unlevered_fcf"] = df["nopat"] + df["da"] - df["capex"] - df["nwc_change"]

    return df
