import json

import pandas as pd
from typer.testing import CliRunner

from stock_trade.cli import app
from stock_trade.execution.planner import (
    TradePlan,
    TradePlanItem,
    build_trade_plan,
    filter_trade_plan_by_consistency,
    resize_trade_plan,
)
from stock_trade.risk import RiskLimits


def test_paper_execute_without_yes_is_dry_run(tmp_path) -> None:
    plan_path = tmp_path / "trade_plan.json"
    plan_path.write_text(
        json.dumps(TradePlan(
            generated_at="2026-06-02T00:00:00+00:00",
            account_equity=100_000,
            mode="paper",
            items=[],
        ).to_dict()),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["paper-execute", "--plan-file", str(plan_path)])

    assert result.exit_code == 0
    assert "Dry run only" in result.output


def test_paper_execute_with_yes_requires_consistency_summary(tmp_path) -> None:
    plan_path = tmp_path / "trade_plan.json"
    plan_path.write_text(
        json.dumps(
            TradePlan(
                generated_at="2026-06-02T00:00:00+00:00",
                account_equity=100_000,
                mode="paper",
                items=[],
            ).to_dict()
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "paper-execute",
            "--plan-file",
            str(plan_path),
            "--walk-forward-summary",
            str(tmp_path / "missing.csv"),
            "--yes",
        ],
    )

    assert result.exit_code != 0
    assert "Walk-forward consistency summary is required" in result.output


def test_trade_plan_ranks_by_score_not_test_sharpe() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "validation_winner",
                "latest_signal": True,
                "score": 2.0,
                "validation_sharpe": 2.0,
                "validation_max_drawdown": -0.05,
                "test_sharpe": 0.1,
                "test_max_drawdown": -0.05,
                "params": "{}",
            },
            {
                "symbol": "QQQ",
                "strategy": "test_winner",
                "latest_signal": True,
                "score": 0.5,
                "validation_sharpe": 0.5,
                "validation_max_drawdown": -0.05,
                "test_sharpe": 10.0,
                "test_max_drawdown": -0.05,
                "params": "{}",
            },
        ]
    )
    limits = RiskLimits(
        max_positions=1,
        max_position_pct=0.9,
        cash_buffer_pct=0.1,
        max_drawdown_pct=0.25,
        min_validation_sharpe=0.1,
    )

    plan = build_trade_plan(leaderboard, account_equity=100_000, limits=limits)

    assert [item.symbol for item in plan.items] == ["SPY"]


def test_trade_plan_respects_cash_buffer() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": symbol,
                "strategy": "strategy",
                "latest_signal": True,
                "score": 1.0,
                "validation_sharpe": 1.0,
                "validation_max_drawdown": -0.05,
                "test_sharpe": 1.0,
                "test_max_drawdown": -0.05,
                "params": "{}",
            }
            for symbol in ["SPY", "QQQ", "IWM"]
        ]
    )
    limits = RiskLimits(
        max_positions=3,
        max_position_pct=0.8,
        cash_buffer_pct=0.25,
        max_drawdown_pct=0.25,
        min_validation_sharpe=0.1,
    )

    plan = build_trade_plan(leaderboard, account_equity=100_000, limits=limits)

    assert sum(item.target_notional for item in plan.items) <= 75_000


def test_trade_plan_clamps_target_weight_when_cash_buffer_exceeds_equity() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "strategy",
                "latest_signal": True,
                "score": 1.0,
                "validation_sharpe": 1.0,
                "validation_max_drawdown": -0.05,
                "test_sharpe": 1.0,
                "test_max_drawdown": -0.05,
                "params": "{}",
            }
        ]
    )
    limits = RiskLimits(
        max_positions=1,
        max_position_pct=0.8,
        cash_buffer_pct=1.25,
        max_drawdown_pct=0.25,
        min_validation_sharpe=0.1,
    )

    plan = build_trade_plan(leaderboard, account_equity=100_000, limits=limits)

    assert plan.items[0].target_weight == 0.0
    assert plan.items[0].target_notional == 0.0


def test_resize_trade_plan_preserves_plan_timestamp() -> None:
    plan = TradePlan(
        generated_at="2026-06-02T00:00:00+00:00",
        account_equity=100_000,
        mode="paper",
        items=[
            TradePlanItem(
                symbol="SPY",
                strategy="strategy",
                target_weight=0.25,
                target_notional=25_000,
                score=1.0,
                validation_sharpe=1.0,
                test_sharpe=1.0,
                test_max_drawdown=-0.05,
                params="{}",
            )
        ],
    )
    limits = RiskLimits(
        max_positions=3,
        max_position_pct=0.25,
        cash_buffer_pct=0.1,
        max_drawdown_pct=0.25,
        min_validation_sharpe=0.1,
    )

    resized = resize_trade_plan(plan, account_equity=200_000, limits=limits)

    assert resized.generated_at == plan.generated_at


def test_filter_trade_plan_by_consistency_keeps_only_consistent_items() -> None:
    plan = TradePlan(
        generated_at="2026-06-02T00:00:00+00:00",
        account_equity=100_000,
        mode="paper",
        items=[
            TradePlanItem(
                symbol="SPY",
                strategy="swing_momentum_5_20",
                target_weight=0.25,
                target_notional=25_000,
                score=1.0,
                validation_sharpe=1.0,
                test_sharpe=1.0,
                test_max_drawdown=-0.05,
                params='{"exit_window": 3}',
            ),
            TradePlanItem(
                symbol="QQQ",
                strategy="swing_breakout_20_exit_10",
                target_weight=0.25,
                target_notional=25_000,
                score=1.0,
                validation_sharpe=1.0,
                test_sharpe=1.0,
                test_max_drawdown=-0.05,
                params='{"exit_window": 10}',
            ),
        ],
    )
    summary = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "swing_momentum_5_20",
                "params": '{"exit_window": 3}',
                "consistent": True,
            },
            {
                "symbol": "QQQ",
                "strategy": "swing_breakout_20_exit_10",
                "params": '{"exit_window": 10}',
                "consistent": False,
            },
        ]
    )

    filtered = filter_trade_plan_by_consistency(plan, summary)

    assert [item.symbol for item in filtered.items] == ["SPY"]
    assert filtered.account_equity == plan.account_equity
    assert filtered.generated_at == plan.generated_at