import json
from dataclasses import asdict

import pandas as pd

from stock_trade.research.backtest import run_long_only_backtest, slice_result
from stock_trade.research.strategies import StrategySpec, strategy_specs


def run_strategy_sweep(
    close: pd.DataFrame,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
    specs: list[StrategySpec] | None = None,
) -> pd.DataFrame:
    specs = specs or strategy_specs()
    rows: list[dict[str, object]] = []

    for symbol in close.columns:
        series = close[symbol].dropna()
        if len(series) < 504:
            continue

        train_end, validation_end = _split_points(series.index)
        train_start = series.index[0]
        validation_start = series.index[train_end]
        test_start = series.index[validation_end]
        end = series.index[-1]

        for spec in specs:
            raw_position = spec.build_position(series)
            full_result = run_long_only_backtest(
                series,
                raw_position,
                initial_cash=initial_cash,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
            )
            train = slice_result(full_result, train_start, series.index[train_end - 1])
            validation = slice_result(
                full_result,
                validation_start,
                series.index[validation_end - 1],
            )
            test = slice_result(full_result, test_start, end)
            score = _score(validation.metrics.sharpe, validation.metrics.max_drawdown)

            rows.append(
                {
                    "symbol": symbol,
                    "strategy": spec.name,
                    "kind": spec.kind,
                    "params": json.dumps(spec.params, sort_keys=True),
                    "latest_signal": bool(raw_position.iloc[-1] > 0),
                    "score": score,
                    **_prefix_metrics("train", train.metrics),
                    **_prefix_metrics("validation", validation.metrics),
                    **_prefix_metrics("test", test.metrics),
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["score", "validation_sharpe"], ascending=False)


def _split_points(index: pd.Index) -> tuple[int, int]:
    train_end = max(int(len(index) * 0.60), 1)
    validation_end = max(int(len(index) * 0.80), train_end + 1)
    return train_end, validation_end


def _prefix_metrics(prefix: str, metrics: object) -> dict[str, float | int]:
    return {f"{prefix}_{key}": value for key, value in asdict(metrics).items()}


def _score(validation_sharpe: float, validation_max_drawdown: float) -> float:
    drawdown_penalty = abs(min(0.0, validation_max_drawdown)) * 1.5
    return validation_sharpe - drawdown_penalty