"""Generates the summary chart(s) saved to outputs/figures/."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

FIGURES_DIR = Path(__file__).parent.parent.parent / "outputs" / "figures"


def plot_valuation_summary(
    dcf_base_price: float,
    dcf_low_price: float,
    dcf_high_price: float,
    comps_low_price: float,
    comps_median_price: float,
    comps_high_price: float,
    current_price: float,
    ticker: str = "CMG",
) -> Path:
    """Horizontal range chart: DCF sensitivity range vs comps range vs current price."""
    fig, ax = plt.subplots(figsize=(9, 4))

    rows = [
        ("DCF (sensitivity range)", dcf_low_price, dcf_high_price, dcf_base_price),
        ("Comps (peer min-max)", comps_low_price, comps_high_price, comps_median_price),
    ]

    y_positions = range(len(rows))
    for y, (label, low, high, point) in zip(y_positions, rows):
        ax.plot([low, high], [y, y], color="#4C72B0", linewidth=6, solid_capstyle="round", alpha=0.5)
        ax.scatter([point], [y], color="#4C72B0", s=90, zorder=3, label="_nolegend_")
        ax.annotate(f"${low:.0f}", (low, y), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=9)
        ax.annotate(f"${high:.0f}", (high, y), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=9)
        ax.annotate(f"${point:.0f}", (point, y), textcoords="offset points", xytext=(0, -16), ha="center", fontsize=9, fontweight="bold")

    ax.axvline(current_price, color="#C44E52", linestyle="--", linewidth=1.5)
    ax.annotate(
        f"Current price: ${current_price:.2f}",
        (current_price, len(rows) - 0.5),
        textcoords="offset points",
        xytext=(8, 0),
        color="#C44E52",
        fontsize=9,
        fontweight="bold",
    )

    ax.set_yticks(list(y_positions))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel("Implied share price ($)")
    ax.set_title(f"{ticker} — DCF vs. Comparable Companies Implied Valuation")
    ax.set_ylim(-1, len(rows))
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "valuation_summary.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_revenue_projection(projection_df: pd.DataFrame, base_revenue: float, base_year: int, ticker: str = "CMG") -> Path:
    fig, ax = plt.subplots(figsize=(8, 4))
    years = [base_year] + list(projection_df.index)
    revenues = [base_revenue / 1e9] + list(projection_df["revenue"] / 1e9)

    ax.bar([str(y) for y in years], revenues, color=["#888888"] + ["#4C72B0"] * len(projection_df))
    ax.set_ylabel("Revenue ($B)")
    ax.set_title(f"{ticker} — Projected Revenue")
    ax.spines[["top", "right"]].set_visible(False)
    for i, v in enumerate(revenues):
        ax.annotate(f"${v:.1f}B", (i, v), textcoords="offset points", xytext=(0, 4), ha="center", fontsize=8)
    fig.tight_layout()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "revenue_projection.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_scenarios(scenarios_df: pd.DataFrame, current_price: float, ticker: str = "CMG") -> Path:
    """Bar chart of implied share price under bear / base / bull operating cases.

    Bars are coloured against the market price rather than by scenario name, so
    the chart answers the only question that matters at a glance: which of these
    cases would have to be true for the stock to be worth what it costs.
    """
    order = [s for s in ("bear", "base", "bull") if s in scenarios_df.index]
    prices = [scenarios_df.loc[s, "implied_share_price"] for s in order]
    colors = ["#55A868" if p >= current_price else "#4C72B0" for p in prices]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar([s.capitalize() for s in order], prices, color=colors, width=0.55)

    for bar, scenario, price in zip(bars, order, prices):
        upside = scenarios_df.loc[scenario, "upside_vs_market"]
        margin = scenarios_df.loc[scenario, "exit_operating_margin"]
        ax.annotate(
            f"${price:.2f}\n{upside:+.0%}",
            (bar.get_x() + bar.get_width() / 2, price),
            textcoords="offset points",
            xytext=(0, 6),
            ha="center",
            fontsize=10,
            fontweight="bold",
        )
        ax.annotate(
            f"exit margin {margin:.1%}",
            (bar.get_x() + bar.get_width() / 2, 0),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
            color="white",
        )

    ax.axhline(current_price, color="#C44E52", linestyle="--", linewidth=1.5)
    ax.annotate(
        f"Current price: ${current_price:.2f}",
        # x in axes fraction, y in data coords. Anchoring x in data coords is
        # fragile here: matplotlib silently drops an annotation whose anchor
        # falls outside the axis limits, and the limits of a categorical axis
        # move with the bar width, so a hardcoded x can vanish without error.
        (0.01, current_price),
        xycoords=("axes fraction", "data"),
        textcoords="offset points",
        xytext=(0, 6),
        ha="left",
        color="#C44E52",
        fontsize=9,
        fontweight="bold",
    )

    ax.set_ylabel("Implied share price ($)")
    ax.set_title(f"{ticker} — Implied Value by Operating Scenario")
    ax.set_ylim(0, max(max(prices), current_price) * 1.25)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "scenarios.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
