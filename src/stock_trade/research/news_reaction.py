from __future__ import annotations

from dataclasses import dataclass
from random import Random

import pandas as pd

from stock_trade.news.models import NewsEvent


@dataclass(frozen=True)
class NewsReactionReport:
    samples: pd.DataFrame
    summary: pd.DataFrame


def evaluate_news_reactions(
    events: list[NewsEvent],
    close: pd.DataFrame,
    horizons: tuple[int, ...] = (1, 3, 5, 10),
    fee_bps: float = 1.0,
    slippage_bps: float = 5.0,
    random_seed: int = 0,
) -> NewsReactionReport:
    prices = close.sort_index().astype(float)
    samples = _build_samples(events, prices, horizons, fee_bps, slippage_bps, random_seed)
    return NewsReactionReport(samples=samples, summary=_summarize_samples(samples))


def _build_samples(
    events: list[NewsEvent],
    close: pd.DataFrame,
    horizons: tuple[int, ...],
    fee_bps: float,
    slippage_bps: float,
    random_seed: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    cost_rate = (fee_bps + slippage_bps) * 2 / 10_000
    random = Random(random_seed)

    for event in events:
        for symbol in event.symbols:
            if symbol not in close.columns:
                continue
            series = close[symbol].dropna()
            entry_index = _entry_index_after_received(series.index, event.received_timestamp)
            if entry_index is None:
                continue
            for horizon in horizons:
                exit_index = entry_index + horizon
                if exit_index >= len(series):
                    continue
                baseline_entry_index = _baseline_entry_index(
                    random=random,
                    series_length=len(series),
                    horizon=horizon,
                )
                forward_return = _forward_return(series, entry_index, horizon)
                baseline_return = _forward_return(series, baseline_entry_index, horizon)
                rows.append(
                    {
                        "provider": event.provider,
                        "provider_event_id": event.provider_event_id,
                        "symbol": symbol,
                        "event_type": event.event_type.value,
                        "provider_timestamp": event.provider_timestamp.isoformat(),
                        "received_timestamp": event.received_timestamp.isoformat(),
                        "entry_timestamp": series.index[entry_index].isoformat(),
                        "exit_timestamp": series.index[exit_index].isoformat(),
                        "horizon": horizon,
                        "forward_return": forward_return,
                        "net_return": forward_return - cost_rate,
                        "baseline_net_return": baseline_return - cost_rate,
                    }
                )

    return pd.DataFrame(rows)


def _summarize_samples(samples: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame()

    grouped = samples.groupby(["symbol", "event_type", "horizon"], as_index=False).agg(
        event_count=("provider_event_id", "count"),
        hit_rate=("net_return", lambda values: float((values > 0).mean())),
        avg_forward_return=("forward_return", "mean"),
        avg_net_return=("net_return", "mean"),
        baseline_avg_net_return=("baseline_net_return", "mean"),
        turnover=("provider_event_id", "count"),
    )
    grouped["beats_baseline"] = grouped["avg_net_return"] > grouped["baseline_avg_net_return"]
    drawdowns = (
        samples.sort_values(["symbol", "event_type", "horizon", "received_timestamp"])
        .groupby(["symbol", "event_type", "horizon"])["net_return"]
        .apply(_max_drawdown_from_returns)
        .reset_index(name="max_drawdown")
    )
    return grouped.merge(drawdowns, on=["symbol", "event_type", "horizon"]).sort_values(
        ["avg_net_return", "hit_rate"],
        ascending=False,
    )


def _entry_index_after_received(index: pd.Index, received_timestamp: object) -> int | None:
    received = pd.Timestamp(received_timestamp)
    if received.tzinfo is None and getattr(index, "tz", None) is not None:
        received = received.tz_localize(index.tz)
    matches = index.searchsorted(received, side="right")
    return int(matches) if matches < len(index) else None


def _baseline_entry_index(random: Random, series_length: int, horizon: int) -> int:
    max_entry_index = max(0, series_length - horizon - 1)
    return random.randint(0, max_entry_index)


def _forward_return(series: pd.Series, entry_index: int, horizon: int) -> float:
    entry_price = float(series.iloc[entry_index])
    exit_price = float(series.iloc[entry_index + horizon])
    return round((exit_price / entry_price) - 1, 10)


def _max_drawdown_from_returns(returns: pd.Series) -> float:
    cumulative = []
    value = 1.0
    for return_value in returns:
        value *= 1 + float(return_value)
        cumulative.append(value)
    if not cumulative:
        return 0.0
    running_max = []
    current_max = cumulative[0]
    for value in cumulative:
        current_max = max(current_max, value)
        running_max.append(current_max)
    drawdowns = [value / peak - 1 for value, peak in zip(cumulative, running_max, strict=True)]
    return float(min(drawdowns))