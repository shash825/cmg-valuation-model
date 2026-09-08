"""Pulls company financials from yfinance and caches them locally.

Caching matters here for reproducibility: yfinance reflects live market data,
so re-running the model next week would silently change the output. Every
pull is snapshotted to src/data/cache/ with the pull date in the filename;
by default we reuse the newest cached snapshot instead of hitting the network
again.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import yfinance as yf

CACHE_DIR = Path(__file__).parent / "cache"


@dataclass
class CompanySnapshot:
    ticker: str
    name: str
    price: float
    shares_diluted: float
    market_cap: float
    total_debt: float
    cash: float
    beta: float
    revenue: float
    ebitda: float
    operating_income: float
    net_income: float
    diluted_eps: float
    ev_to_ebitda: float
    ev_to_revenue: float
    trailing_pe: float
    revenue_growth: float


def _cache_path(ticker: str) -> Path:
    return CACHE_DIR / f"{ticker}_{date.today().isoformat()}.json"


def _latest_cache(ticker: str) -> Path | None:
    matches = sorted(CACHE_DIR.glob(f"{ticker}_*.json"))
    return matches[-1] if matches else None


def fetch_company_snapshot(ticker: str, use_cache: bool = True) -> CompanySnapshot:
    """Pulls the current fundamentals needed for both the DCF and comps analysis."""
    if use_cache:
        cached = _latest_cache(ticker)
        if cached is not None:
            data = json.loads(cached.read_text())
            return CompanySnapshot(**data)

    t = yf.Ticker(ticker)
    info = t.info
    fin = t.financials

    def _row(name: str, col: int = 0) -> float:
        if name in fin.index:
            val = fin.loc[name].iloc[col]
            return float(val) if val == val else 0.0  # filter NaN
        return 0.0

    snapshot = CompanySnapshot(
        ticker=ticker,
        name=info.get("longName", ticker),
        price=info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
        shares_diluted=_row("Diluted Average Shares") or info.get("sharesOutstanding", 0.0),
        market_cap=info.get("marketCap", 0.0),
        total_debt=info.get("totalDebt", 0.0),
        cash=info.get("totalCash", 0.0),
        beta=info.get("beta", 1.0),
        revenue=_row("Total Revenue"),
        ebitda=_row("EBITDA"),
        operating_income=_row("Operating Income"),
        net_income=_row("Net Income"),
        diluted_eps=_row("Diluted EPS"),
        ev_to_ebitda=info.get("enterpriseToEbitda", 0.0),
        ev_to_revenue=info.get("enterpriseToRevenue", 0.0),
        trailing_pe=info.get("trailingPE", 0.0),
        revenue_growth=info.get("revenueGrowth", 0.0),
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(ticker).write_text(json.dumps(asdict(snapshot), indent=2))
    return snapshot


def fetch_risk_free_rate(use_cache: bool = True) -> float:
    """10Y US Treasury yield (^TNX), quoted as e.g. 4.8 -> returned as 0.048."""
    cache_file = CACHE_DIR / f"risk_free_rate_{date.today().isoformat()}.json"
    if use_cache and cache_file.exists():
        return json.loads(cache_file.read_text())["rate"]

    hist = yf.Ticker("^TNX").history(period="5d")
    rate = float(hist["Close"].iloc[-1]) / 100.0

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps({"rate": rate}))
    return rate


def fetch_comp_snapshots(tickers: list[str], use_cache: bool = True) -> list[CompanySnapshot]:
    return [fetch_company_snapshot(tk, use_cache=use_cache) for tk in tickers]
