import json
from pathlib import Path

import pandas as pd

from stock_trade.config import Settings
from stock_trade.research.loop import run_research_loop
from stock_trade.research.strategies import StrategySpec


def test_research_loop_writes_gated_artifacts_without_execution(tmp_path: Path) -> None:
    def always_long(close: pd.Series) -> pd.Series:
        return pd.Series(1.0, index=close.index)

    close = pd.DataFrame(
        {"QQQ": [100 + index for index in range(48)]},
        index=pd.date_range("2024-01-01", periods=48, freq="D"),
    )
    settings = Settings(
        initial_cash=100_000,
        fee_bps=0,
        slippage_bps=0,
        min_validation_sharpe=0,
        max_drawdown_pct=0.25,
    )

    results = run_research_loop(
        close=close,
        settings=settings,
        output_dir=tmp_path,
        iterations=2,
        train_size=20,
        validation_size=5,
        test_size=5,
        step_size=5,
        specs=[StrategySpec("always_long", "test", {}, always_long)],
    )

    assert [result.iteration for result in results] == [1, 2]
    assert all(result.consistent_items == 1 for result in results)
    assert all(result.submitted_order_count == 0 for result in results)

    consistent_plan = json.loads((tmp_path / "consistent_trade_plan.json").read_text())
    assert consistent_plan["items"][0]["symbol"] == "QQQ"

    summary = pd.read_csv(tmp_path / "research_loop_summary.csv")
    assert list(summary["iteration"]) == [1, 2]
    assert list(summary["consistent_items"]) == [1, 1]