from collections.abc import Iterable
from datetime import date

import pandas as pd


def normalize_symbols(symbols: str | Iterable[str]) -> list[str]:
    parts = symbols.split(",") if isinstance(symbols, str) else symbols
    normalized = [symbol.strip().upper() for symbol in parts if symbol and symbol.strip()]
    if not normalized:
        raise ValueError("At least one symbol is required.")
    return list(dict.fromkeys(normalized))


def fetch_adjusted_close(
    symbols: list[str],
    start: str,
    end: str | date | None = None,
) -> pd.DataFrame:
    import yfinance as yf

    requested_symbols = normalize_symbols(symbols)
    raw = yf.download(
        tickers=requested_symbols,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        group_by="column",
        threads=False,
    )
    if raw.empty:
        raise RuntimeError("No price data returned. Check symbols and date range.")

    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" in raw.columns.get_level_values(0):
            close = raw["Close"]
        elif "Close" in raw.columns.get_level_values(-1):
            close = raw.xs("Close", axis=1, level=-1)
        else:
            raise RuntimeError("Could not locate close prices in downloaded data.")
    else:
        if "Close" not in raw.columns:
            raise RuntimeError("Could not locate close prices in downloaded data.")
        close = raw[["Close"]].rename(columns={"Close": requested_symbols[0]})

    close = close.sort_index().dropna(how="all")
    close.columns = [str(symbol).upper() for symbol in close.columns]
    close = close.loc[:, close.notna().sum() > 252]
    missing_symbols = sorted(set(requested_symbols) - set(close.columns))
    if missing_symbols:
        raise RuntimeError(
            "Missing or insufficient price history for: " + ", ".join(missing_symbols)
        )
    if close.empty:
        raise RuntimeError("Downloaded data has insufficient history after cleaning.")
    return close.ffill()