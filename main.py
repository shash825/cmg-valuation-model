"""Runs the full CMG valuation: DCF + comparable companies analysis.

Usage:
    python main.py

Reads all assumptions from config/assumptions.yaml, pulls (or reuses cached)
financial data via yfinance, and writes tables to outputs/tables/ and charts
to outputs/figures/.
"""

from __future__ import annotations

import yaml

from src.comps.implied_valuation import implied_valuation_from_comps
from src.comps.peer_data import build_comps_table, peer_summary_stats
from src.data.fetch import fetch_comp_snapshots, fetch_company_snapshot, fetch_risk_free_rate
from src.dcf.projections import build_fcf_projection
from src.dcf.sensitivity import implied_share_price, sensitivity_table
from src.dcf.terminal_value import enterprise_value, gordon_growth_terminal_value
from src.dcf.wacc import compute_wacc
from src.output.charts import plot_revenue_projection, plot_valuation_summary
from src.output.report import save_table


def main() -> None:
    assumptions = yaml.safe_load(open("config/assumptions.yaml"))
    ticker = assumptions["target"]["ticker"]
    base_year = assumptions["target"]["base_fiscal_year"]

    print(f"=== {ticker} Valuation Model ===\n")

    # --- Pull data ---
    print("Fetching target company data...")
    target = fetch_company_snapshot(ticker)
    risk_free_rate = assumptions["wacc"].get("risk_free_rate") or fetch_risk_free_rate()

    print("Fetching comparable companies data...")
    peers = fetch_comp_snapshots(assumptions["comps"]["tickers"])

    # --- DCF ---
    print("\nBuilding DCF projection...")
    projection = build_fcf_projection(target.revenue, base_year, assumptions)
    save_table(projection, "dcf_projection")

    wacc = compute_wacc(
        risk_free_rate=risk_free_rate,
        beta=target.beta,
        equity_risk_premium=assumptions["wacc"]["equity_risk_premium"],
    )
    print(f"WACC (cost of equity): {wacc:.2%}")

    fcfs = projection["unlevered_fcf"].tolist()
    terminal_growth = assumptions["dcf"]["terminal_growth_rate"]
    tv = gordon_growth_terminal_value(fcfs[-1], wacc, terminal_growth)
    ev_result = enterprise_value(fcfs, tv, wacc)

    net_debt = target.total_debt - target.cash
    equity_value = ev_result["enterprise_value"] - net_debt
    dcf_price = equity_value / target.shares_diluted

    print(f"Enterprise value: ${ev_result['enterprise_value']/1e9:.2f}B")
    print(f"Net debt (capitalized leases - cash): ${net_debt/1e9:.2f}B")
    print(f"Equity value: ${equity_value/1e9:.2f}B")
    print(f"DCF implied share price: ${dcf_price:.2f}")

    sens = sensitivity_table(
        fcfs,
        assumptions["dcf"]["sensitivity"]["wacc_range"],
        assumptions["dcf"]["sensitivity"]["terminal_growth_range"],
        net_debt,
        target.shares_diluted,
    )
    save_table(sens, "dcf_sensitivity")

    dcf_low = sens.min().min()
    dcf_high = sens.max().max()

    # --- Comps ---
    print("\nBuilding comps table...")
    comps_df = build_comps_table(peers)
    save_table(comps_df, "comps_table")

    peer_stats = peer_summary_stats(comps_df)
    save_table(peer_stats, "comps_peer_stats")

    implied_df = implied_valuation_from_comps(target, peer_stats)
    save_table(implied_df, "comps_implied_valuation")

    # P/E is excluded from the headline range: CAVA's ~107x P/E (a hyper-growth
    # outlier) and SG's near-zero GAAP earnings make P/E an unreliable
    # cross-sectional comparison for this peer set. EV/Revenue and EV/EBITDA
    # are capital-structure- and earnings-quality-agnostic and used as the
    # primary comps range instead. Full P/E detail is still saved to the table.
    primary = implied_df[implied_df["multiple"] != "P/E"]
    comps_low = primary["implied_share_price"].min()
    comps_high = primary["implied_share_price"].max()
    comps_median = primary.loc[primary["stat"] == "median", "implied_share_price"].mean()

    print(f"Comps implied share price range (EV/Revenue & EV/EBITDA): ${comps_low:.2f} - ${comps_high:.2f} (median-multiple midpoint ${comps_median:.2f})")

    # --- Charts ---
    print("\nGenerating charts...")
    plot_valuation_summary(
        dcf_base_price=dcf_price,
        dcf_low_price=dcf_low,
        dcf_high_price=dcf_high,
        comps_low_price=comps_low,
        comps_median_price=comps_median,
        comps_high_price=comps_high,
        current_price=target.price,
        ticker=ticker,
    )
    plot_revenue_projection(projection, target.revenue, base_year, ticker)

    print(f"\nCurrent market price: ${target.price:.2f}")
    print("\nDone. See outputs/tables/ and outputs/figures/.")


if __name__ == "__main__":
    main()
