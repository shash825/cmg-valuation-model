"""Saves DataFrames/results to outputs/tables/ as CSV and Markdown."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

TABLES_DIR = Path(__file__).parent.parent.parent / "outputs" / "tables"


def save_table(df: pd.DataFrame, name: str) -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES_DIR / f"{name}.csv")
    (TABLES_DIR / f"{name}.md").write_text(df.to_markdown())
