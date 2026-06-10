import pandas as pd
import pytest

from stock_trade.research.backtest import run_long_only_backtest, slice_result


def test_backtest_uses_next_bar_exposure() -> None:
    close = pd.Series([100.0, 110.0, 121.0], index=pd.date_range("2024-01-01", periods=3))
    position = pd.Series([1.0, 1.0, 1.0], index=close.index)

    result = run_long_only_backtest(close, position, initial_cash=1000, fee_bps=0, slippage_bps=0)

    assert result.returns.iloc[0] == 0
    assert result.returns.iloc[1] == pytest.approx(0.10)
    assert round(result.equity.iloc[-1], 2) == 1210.0


def test_backtest_charges_turnover_costs() -> None:
    close = pd.Series([100.0, 100.0, 100.0], index=pd.date_range("2024-01-01", periods=3))
    position = pd.Series([1.0, 0.0, 1.0], index=close.index)

    result = run_long_only_backtest(close, position, initial_cash=1000, fee_bps=10, slippage_bps=0)

    assert result.equity.iloc[-1] < 1000


def test_slice_result_includes_first_sliced_return_in_drawdown() -> None:
    close = pd.Series([100.0, 80.0, 80.0, 80.0], index=pd.date_range("2024-01-01", periods=4))
    position = pd.Series([1.0, 1.0, 1.0, 1.0], index=close.index)

    result = run_long_only_backtest(close, position, initial_cash=1000, fee_bps=0, slippage_bps=0)
    sliced = slice_result(result, close.index[1], close.index[-1])

    assert sliced.metrics.total_return == pytest.approx(-0.20)
    assert sliced.metrics.max_drawdown == pytest.approx(-0.20)