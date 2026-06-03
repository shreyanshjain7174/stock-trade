from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from stock_trade.config import Settings
from stock_trade.execution.planner import (
    TradePlan,
    build_trade_plan,
    filter_trade_plan_by_consistency,
)
from stock_trade.research.strategies import StrategySpec
from stock_trade.research.sweep import run_strategy_sweep
from stock_trade.research.walk_forward import run_walk_forward, summarize_walk_forward
from stock_trade.risk import RiskLimits


@dataclass(frozen=True)
class ResearchLoopResult:
    iteration: int
    leaderboard_rows: int
    plan_items: int
    consistent_items: int
    submitted_order_count: int = 0


def run_research_loop(
    close: pd.DataFrame,
    settings: Settings,
    output_dir: Path,
    iterations: int,
    train_size: int = 504,
    validation_size: int = 126,
    test_size: int = 126,
    step_size: int = 126,
    specs: list[StrategySpec] | None = None,
) -> list[ResearchLoopResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    iteration_count = max(1, iterations)
    results: list[ResearchLoopResult] = []
    limits = _risk_limits(settings)

    for iteration in range(1, iteration_count + 1):
        split_sizes = (train_size, validation_size, test_size)
        leaderboard = run_strategy_sweep(
            close=close,
            initial_cash=settings.initial_cash,
            fee_bps=settings.fee_bps,
            slippage_bps=settings.slippage_bps,
            specs=specs,
            split_sizes=split_sizes if len(close.index) < 504 else None,
        )
        windows = run_walk_forward(
            close=close,
            initial_cash=settings.initial_cash,
            fee_bps=settings.fee_bps,
            slippage_bps=settings.slippage_bps,
            train_size=train_size,
            validation_size=validation_size,
            test_size=test_size,
            step_size=step_size,
            specs=specs,
        )
        summary = summarize_walk_forward(
            windows,
            min_validation_sharpe=settings.min_validation_sharpe,
            max_drawdown_pct=settings.max_drawdown_pct,
        )
        plan = build_trade_plan(leaderboard, account_equity=settings.initial_cash, limits=limits)
        consistent_plan = filter_trade_plan_by_consistency(plan, summary)

        _write_iteration_artifacts(output_dir, leaderboard, windows, summary, plan, consistent_plan)
        results.append(
            ResearchLoopResult(
                iteration=iteration,
                leaderboard_rows=len(leaderboard),
                plan_items=len(plan.items),
                consistent_items=len(consistent_plan.items),
            )
        )

    pd.DataFrame([asdict(result) for result in results]).to_csv(
        output_dir / "research_loop_summary.csv",
        index=False,
    )
    return results


def _write_iteration_artifacts(
    output_dir: Path,
    leaderboard: pd.DataFrame,
    windows: pd.DataFrame,
    summary: pd.DataFrame,
    plan: TradePlan,
    consistent_plan: TradePlan,
) -> None:
    leaderboard.to_csv(output_dir / "leaderboard.csv", index=False)
    windows.to_csv(output_dir / "walk_forward_windows.csv", index=False)
    summary.to_csv(output_dir / "walk_forward_summary.csv", index=False)
    (output_dir / "trade_plan.json").write_text(
        json.dumps(plan.to_dict(), indent=2),
        encoding="utf-8",
    )
    (output_dir / "consistent_trade_plan.json").write_text(
        json.dumps(consistent_plan.to_dict(), indent=2),
        encoding="utf-8",
    )


def _risk_limits(settings: Settings) -> RiskLimits:
    return RiskLimits(
        max_positions=settings.max_positions,
        max_position_pct=settings.max_position_pct,
        cash_buffer_pct=settings.cash_buffer_pct,
        max_drawdown_pct=settings.max_drawdown_pct,
        min_validation_sharpe=settings.min_validation_sharpe,
    )