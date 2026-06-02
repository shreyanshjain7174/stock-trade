import pandas as pd

from stock_trade.research.walk_forward import run_walk_forward, summarize_walk_forward


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SPY": [100 + index * 0.15 + ((index % 11) * 0.08) for index in range(900)],
            "QQQ": [120 + index * 0.20 + ((index % 13) * 0.07) for index in range(900)],
        },
        index=pd.date_range("2020-01-01", periods=900, freq="D"),
    )


def test_walk_forward_runs_rolling_strategy_sweeps() -> None:
    windows = run_walk_forward(
        close=_prices(),
        initial_cash=100_000,
        fee_bps=1,
        slippage_bps=5,
        train_size=252,
        validation_size=126,
        test_size=126,
        step_size=126,
    )

    assert not windows.empty
    assert {"SPY", "QQQ"}.issubset(set(windows["symbol"]))
    assert {"window_id", "window_start", "window_end"}.issubset(windows.columns)
    assert windows["window_id"].nunique() >= 3
    assert windows["test_trades"].min() >= 0


def test_walk_forward_summary_scores_consistency() -> None:
    windows = run_walk_forward(
        close=_prices(),
        initial_cash=100_000,
        fee_bps=1,
        slippage_bps=5,
        train_size=252,
        validation_size=126,
        test_size=126,
        step_size=126,
    )

    summary = summarize_walk_forward(
        windows,
        min_validation_sharpe=0.10,
        max_drawdown_pct=0.25,
    )

    assert not summary.empty
    assert {
        "symbol",
        "strategy",
        "params",
        "windows",
        "validation_pass_rate",
        "test_pass_rate",
        "avg_test_sharpe",
        "worst_test_drawdown",
        "consistency_score",
        "consistent",
    }.issubset(summary.columns)
    assert summary.iloc[0]["consistency_score"] >= summary.iloc[-1]["consistency_score"]
    assert summary["validation_pass_rate"].between(0, 1).all()
    assert summary["test_pass_rate"].between(0, 1).all()