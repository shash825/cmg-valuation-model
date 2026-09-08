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
