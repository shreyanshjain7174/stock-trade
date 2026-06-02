import pandas as pd

from stock_trade.research.strategies import (
    strategy_specs,
    swing_breakout_position,
    swing_momentum_position,
    swing_pullback_position,
)


def _swing_prices() -> pd.Series:
    values = []
    price = 100.0
    for index in range(80):
        if index % 18 in {8, 9, 10}:
            price -= 1.0
        elif index % 18 in {11, 12, 13, 14}:
            price += 1.8
        else:
            price += 0.35
        values.append(price)
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values)))


def test_swing_strategy_specs_are_registered() -> None:
    specs = strategy_specs()

    assert "swing_pullback_rsi_3_35_65" in {spec.name for spec in specs}
    assert "swing_breakout_10_exit_5" in {spec.name for spec in specs}
    assert "swing_momentum_5_20" in {spec.name for spec in specs}


def test_swing_pullback_generates_short_window_positions() -> None:
    close = _swing_prices()

    position = swing_pullback_position(close, rsi_window=3, buy_threshold=35, sell_threshold=65)

    assert position.index.equals(close.index)
    assert position.max() == 1.0
    assert 0 < position.mean() < 1


def test_swing_breakout_generates_stateful_positions() -> None:
    close = _swing_prices()

    position = swing_breakout_position(close, lookback=10, exit_window=5)

    assert position.index.equals(close.index)
    assert position.max() == 1.0
    assert 0 < position.mean() < 1


def test_swing_momentum_generates_stateful_positions() -> None:
    close = _swing_prices()

    position = swing_momentum_position(close, momentum_window=5, trend_window=20)

    assert position.index.equals(close.index)
    assert position.max() == 1.0
    assert 0 < position.mean() < 1