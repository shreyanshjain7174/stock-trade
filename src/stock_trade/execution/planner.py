from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from stock_trade.risk import RiskLimits


@dataclass(frozen=True)
class TradePlanItem:
    symbol: str
    strategy: str
    target_weight: float
    target_notional: float
    score: float
    validation_sharpe: float
    test_sharpe: float
    test_max_drawdown: float
    params: str


@dataclass(frozen=True)
class TradePlan:
    generated_at: str
    account_equity: float
    mode: str
    items: list[TradePlanItem]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "account_equity": self.account_equity,
            "mode": self.mode,
            "items": [asdict(item) for item in self.items],
        }


def build_trade_plan(
    leaderboard: pd.DataFrame,
    account_equity: float,
    limits: RiskLimits,
    mode: str = "paper",
) -> TradePlan:
    if leaderboard.empty:
        return _empty_plan(account_equity, mode)

    candidates = leaderboard[leaderboard["latest_signal"]].copy()
    candidates = candidates[
        candidates.apply(
            lambda row: limits.passes_strategy_gate(
                validation_sharpe=float(row["validation_sharpe"]),
                validation_max_drawdown=float(row["validation_max_drawdown"]),
            ),
            axis=1,
        )
    ]
    if candidates.empty:
        return _empty_plan(account_equity, mode)

    selected = (
        candidates.sort_values(["score", "validation_sharpe"], ascending=False)
        .drop_duplicates(subset=["symbol"], keep="first")
        .head(limits.max_positions)
    )
    target_weight = _safe_target_weight(limits, len(selected))

    items = [
        _plan_item_from_row(row, account_equity, limits, target_weight)
        for row in selected.itertuples(index=False)
    ]
    return TradePlan(
        generated_at=datetime.now(UTC).isoformat(),
        account_equity=account_equity,
        mode=mode,
        items=_enforce_cash_buffer(items, account_equity, limits),
    )


def resize_trade_plan(plan: TradePlan, account_equity: float, limits: RiskLimits) -> TradePlan:
    if not plan.items:
        return _empty_plan(account_equity, plan.mode)

    target_weight = _safe_target_weight(limits, len(plan.items))
    resized_items = [
        TradePlanItem(
            symbol=item.symbol,
            strategy=item.strategy,
            target_weight=target_weight,
            target_notional=min(
                account_equity * target_weight,
                limits.max_position_notional(account_equity),
            ),
            score=item.score,
            validation_sharpe=item.validation_sharpe,
            test_sharpe=item.test_sharpe,
            test_max_drawdown=item.test_max_drawdown,
            params=item.params,
        )
        for item in plan.items
    ]
    return TradePlan(
        generated_at=plan.generated_at,
        account_equity=account_equity,
        mode=plan.mode,
        items=_enforce_cash_buffer(resized_items, account_equity, limits),
    )


def _plan_item_from_row(
    row: object,
    account_equity: float,
    limits: RiskLimits,
    target_weight: float,
) -> TradePlanItem:
    size_multiplier = float(getattr(row, "agent_size_multiplier", 1.0))
    adjusted_weight = target_weight * max(0.0, min(size_multiplier, 1.0))
    return TradePlanItem(
        symbol=str(row.symbol),
        strategy=str(row.strategy),
        target_weight=adjusted_weight,
        target_notional=min(
            account_equity * adjusted_weight,
            limits.max_position_notional(account_equity),
        ),
        score=float(row.score),
        validation_sharpe=float(row.validation_sharpe),
        test_sharpe=float(row.test_sharpe),
        test_max_drawdown=float(row.test_max_drawdown),
        params=str(row.params),
    )


def _safe_target_weight(limits: RiskLimits, selected_count: int) -> float:
    if selected_count <= 0:
        return 0.0
    return min(limits.max_position_pct, (1.0 - limits.cash_buffer_pct) / selected_count)


def _enforce_cash_buffer(
    items: list[TradePlanItem],
    account_equity: float,
    limits: RiskLimits,
) -> list[TradePlanItem]:
    total_notional = sum(item.target_notional for item in items)
    max_notional = limits.max_deployable_notional(account_equity)
    if total_notional <= max_notional or total_notional <= 0:
        return items

    scale = max_notional / total_notional
    return [
        TradePlanItem(
            symbol=item.symbol,
            strategy=item.strategy,
            target_weight=item.target_weight * scale,
            target_notional=item.target_notional * scale,
            score=item.score,
            validation_sharpe=item.validation_sharpe,
            test_sharpe=item.test_sharpe,
            test_max_drawdown=item.test_max_drawdown,
            params=item.params,
        )
        for item in items
    ]


def _empty_plan(account_equity: float, mode: str) -> TradePlan:
    return TradePlan(
        generated_at=datetime.now(UTC).isoformat(),
        account_equity=account_equity,
        mode=mode,
        items=[],
    )