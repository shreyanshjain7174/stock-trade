from __future__ import annotations

import pandas as pd

from stock_trade.research.strategies import StrategySpec
from stock_trade.research.sweep import run_strategy_sweep


def run_walk_forward(
    close: pd.DataFrame,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
    train_size: int = 504,
    validation_size: int = 126,
    test_size: int = 126,
    step_size: int = 126,
    specs: list[StrategySpec] | None = None,
) -> pd.DataFrame:
    close = close.sort_index()
    total_size = train_size + validation_size + test_size
    if len(close.index) < total_size:
        return pd.DataFrame()

    rows: list[pd.DataFrame] = []
    max_start = len(close.index) - total_size
    for window_id, start_index in enumerate(range(0, max_start + 1, step_size), start=1):
        end_index = start_index + total_size
        window = close.iloc[start_index:end_index]
        leaderboard = run_strategy_sweep(
            close=window,
            initial_cash=initial_cash,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            specs=specs,
        )
        if leaderboard.empty:
            continue
        annotated = leaderboard.copy()
        annotated.insert(0, "window_id", window_id)
        annotated.insert(1, "window_start", window.index[0].isoformat())
        annotated.insert(2, "window_end", window.index[-1].isoformat())
        rows.append(annotated)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def summarize_walk_forward(
    windows: pd.DataFrame,
    min_validation_sharpe: float,
    max_drawdown_pct: float,
) -> pd.DataFrame:
    if windows.empty:
        return pd.DataFrame()

    scored = windows.copy()
    scored["validation_pass"] = (
        (scored["validation_sharpe"] >= min_validation_sharpe)
        & (scored["validation_max_drawdown"] >= -max_drawdown_pct)
    )
    scored["test_pass"] = (
        (scored["test_sharpe"] > 0) & (scored["test_max_drawdown"] >= -max_drawdown_pct)
    )
    scored["latest_signal_rate"] = scored["latest_signal"].astype(float)

    summary = (
        scored.groupby(["symbol", "strategy", "kind", "params"], as_index=False)
        .agg(
            windows=("window_id", "nunique"),
            validation_pass_rate=("validation_pass", "mean"),
            test_pass_rate=("test_pass", "mean"),
            avg_validation_sharpe=("validation_sharpe", "mean"),
            avg_test_sharpe=("test_sharpe", "mean"),
            worst_test_drawdown=("test_max_drawdown", "min"),
            avg_test_trades=("test_trades", "mean"),
            avg_test_exposure=("test_exposure", "mean"),
            avg_test_turnover=("test_turnover", "mean"),
            latest_signal_rate=("latest_signal_rate", "mean"),
        )
        .reset_index(drop=True)
    )
    capped_test_sharpe = summary["avg_test_sharpe"].clip(lower=-2.0, upper=2.0)
    summary["consistency_score"] = (
        summary["validation_pass_rate"]
        + summary["test_pass_rate"]
        + capped_test_sharpe
        - summary["worst_test_drawdown"].abs()
    )
    summary["consistent"] = (
        (summary["windows"] >= 3)
        & (summary["validation_pass_rate"] >= 0.60)
        & (summary["test_pass_rate"] >= 0.50)
        & (summary["worst_test_drawdown"] >= -max_drawdown_pct)
    )
    return summary.sort_values(
        ["consistency_score", "avg_validation_sharpe", "avg_test_sharpe"],
        ascending=False,
    )