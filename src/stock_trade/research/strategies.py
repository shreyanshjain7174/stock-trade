from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

PositionBuilder = Callable[[pd.Series], pd.Series]


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    params: dict[str, int | float]
    build_position: PositionBuilder


def _stateful_position(entry: pd.Series, exit_signal: pd.Series) -> pd.Series:
    in_trade = False
    values: list[float] = []
    for timestamp in entry.index:
        if bool(exit_signal.loc[timestamp]):
            in_trade = False
        if bool(entry.loc[timestamp]):
            in_trade = True
        values.append(1.0 if in_trade else 0.0)
    return pd.Series(values, index=entry.index, name="position")


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=window).mean()
    loss = -delta.clip(upper=0).rolling(window, min_periods=window).mean()
    relative_strength = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + relative_strength))


def trend_position(close: pd.Series, fast: int, slow: int) -> pd.Series:
    fast_ma = close.rolling(fast, min_periods=fast).mean()
    slow_ma = close.rolling(slow, min_periods=slow).mean()
    return ((fast_ma > slow_ma) & (close > slow_ma)).astype(float).fillna(0.0)


def breakout_position(close: pd.Series, lookback: int, exit_window: int) -> pd.Series:
    prior_high = close.rolling(lookback, min_periods=lookback).max().shift(1)
    trailing_mean = close.rolling(exit_window, min_periods=exit_window).mean().shift(1)
    entry = close > prior_high
    exit_signal = close < trailing_mean
    return _stateful_position(entry.fillna(False), exit_signal.fillna(False))


def mean_reversion_position(
    close: pd.Series,
    rsi_window: int,
    buy_threshold: int,
    sell_threshold: int,
    trend_window: int,
) -> pd.Series:
    rsi = _rsi(close, rsi_window)
    trend = close.rolling(trend_window, min_periods=trend_window).mean()
    trend_ok = close > trend
    entry = (rsi < buy_threshold) & trend_ok
    exit_signal = (rsi > sell_threshold) | ~trend_ok
    return _stateful_position(entry.fillna(False), exit_signal.fillna(True))


def _trend_builder(fast: int, slow: int) -> PositionBuilder:
    return lambda close: trend_position(close, fast, slow)


def _breakout_builder(lookback: int, exit_window: int) -> PositionBuilder:
    return lambda close: breakout_position(close, lookback, exit_window)


def _mean_reversion_builder(buy_threshold: int, sell_threshold: int) -> PositionBuilder:
    return lambda close: mean_reversion_position(
        close,
        rsi_window=14,
        buy_threshold=buy_threshold,
        sell_threshold=sell_threshold,
        trend_window=200,
    )


def strategy_specs() -> list[StrategySpec]:
    specs: list[StrategySpec] = []

    for fast, slow in [(20, 100), (50, 150), (50, 200), (100, 200)]:
        specs.append(
            StrategySpec(
                name=f"trend_sma_{fast}_{slow}",
                kind="trend_following",
                params={"fast": fast, "slow": slow},
                build_position=_trend_builder(fast, slow),
            )
        )

    for lookback, exit_window in [(55, 20), (100, 50), (126, 63)]:
        specs.append(
            StrategySpec(
                name=f"breakout_{lookback}_exit_{exit_window}",
                kind="breakout",
                params={"lookback": lookback, "exit_window": exit_window},
                build_position=_breakout_builder(lookback, exit_window),
            )
        )

    for buy_threshold, sell_threshold in [(30, 55), (35, 60)]:
        specs.append(
            StrategySpec(
                name=f"trend_filtered_rsi_{buy_threshold}_{sell_threshold}",
                kind="mean_reversion",
                params={
                    "rsi_window": 14,
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "trend_window": 200,
                },
                build_position=_mean_reversion_builder(buy_threshold, sell_threshold),
            )
        )

    return specs