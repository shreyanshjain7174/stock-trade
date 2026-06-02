import pandas as pd

from stock_trade.execution.planner import build_trade_plan
from stock_trade.research.sweep import run_strategy_sweep
from stock_trade.risk import RiskLimits


def test_research_sweep_and_trade_plan_run_without_network() -> None:
    close = pd.DataFrame(
        {
            "SPY": [100 + (index * 0.20) + ((index % 5) * 0.05) for index in range(620)],
            "QQQ": [120 + (index * 0.25) + ((index % 7) * 0.04) for index in range(620)],
        },
        index=pd.date_range("2020-01-01", periods=620, freq="D"),
    )

    leaderboard = run_strategy_sweep(
        close,
        initial_cash=100_000,
        fee_bps=1,
        slippage_bps=5,
    )
    plan = build_trade_plan(
        leaderboard,
        account_equity=100_000,
        limits=RiskLimits(
            max_positions=3,
            max_position_pct=0.25,
            cash_buffer_pct=0.10,
            max_drawdown_pct=0.25,
            min_validation_sharpe=0.10,
        ),
    )

    assert not leaderboard.empty
    assert {"SPY", "QQQ"}.issubset(set(leaderboard["symbol"]))
    assert plan.items
    assert sum(item.target_notional for item in plan.items) <= 90_000