from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

import pandas as pd

from stock_trade.agents.protocols import CandidateDecision, CommitteeProtocol, RiskDecision
from stock_trade.agents.pseudo_committee import PseudoCommittee
from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.execution.planner import TradePlan, build_trade_plan
from stock_trade.loop.state import LoopMode, LoopState
from stock_trade.research.sweep import run_strategy_sweep
from stock_trade.risk import RiskLimits
from stock_trade.store.sqlite import SQLiteStore


@dataclass(frozen=True)
class RalphRunResult:
    run_id: str
    leaderboard: pd.DataFrame
    plan: TradePlan
    submitted_orders: list[object]


class BrokerProtocol(Protocol):
    def account_equity(self) -> float:
        pass

    def submit_buy_plan(self, plan: TradePlan) -> list[object]:
        pass

    def cancel_open_orders(self) -> int:
        pass


def run_cycle(
    settings: Settings,
    bus: EventBus,
    store: SQLiteStore,
    prices: pd.DataFrame,
    run_id: str | None = None,
    committee: CommitteeProtocol | None = None,
    broker: BrokerProtocol | None = None,
    loop_state: LoopState | None = None,
    execute: bool = False,
) -> RalphRunResult:
    cycle_run_id = run_id or f"ralph-{uuid4()}"
    store.create_run(cycle_run_id, mode=settings.trading_mode, status="started")

    _emit(
        bus,
        store,
        _event(cycle_run_id, EventType.RESEARCH_STARTED, payload={"symbols": list(prices.columns)}),
    )
    leaderboard = run_strategy_sweep(
        close=prices,
        initial_cash=settings.initial_cash,
        fee_bps=settings.fee_bps,
        slippage_bps=settings.slippage_bps,
    )
    _emit(
        bus,
        store,
        _event(
            cycle_run_id,
            EventType.RESEARCH_COMPLETED,
            payload={"candidate_count": int(len(leaderboard))},
        ),
    )

    candidate_reviews = (committee or PseudoCommittee()).review(leaderboard)
    store.save_agent_trace(
        cycle_run_id,
        "committee",
        {"decisions": [_decision_to_dict(review) for review in candidate_reviews]},
    )
    _emit(
        bus,
        store,
        _event(
            cycle_run_id,
            EventType.AGENT_TOOL_CALL,
            payload={"agent": "committee", "decision_count": len(candidate_reviews)},
        ),
    )

    approved_leaderboard = _approved_leaderboard(leaderboard, candidate_reviews)

    state = loop_state or LoopState(mode=LoopMode.RESEARCH)
    account_equity = settings.initial_cash
    if execute and state.can_execute and broker is not None:
        settings.require_paper_trading()
        account_equity = broker.account_equity()

    plan = build_trade_plan(
        approved_leaderboard,
        account_equity=account_equity,
        limits=_risk_limits(settings),
    )
    store.save_plan(cycle_run_id, plan.to_dict())
    _emit(
        bus,
        store,
        _risk_event(cycle_run_id, leaderboard, candidate_reviews, plan),
    )
    _emit(
        bus,
        store,
        _event(
            cycle_run_id,
            EventType.PLAN_CREATED,
            payload={"item_count": len(plan.items)},
        ),
    )
    store.create_run(cycle_run_id, mode=settings.trading_mode, status="planned")

    submitted_orders: list[object] = []
    if execute and state.can_execute and broker is not None:
        submitted_orders = broker.submit_buy_plan(plan)
        _emit(
            bus,
            store,
            _event(
                cycle_run_id,
                EventType.BROKER_ORDER,
                payload={"submitted_order_count": len(submitted_orders)},
            ),
        )

    return RalphRunResult(
        run_id=cycle_run_id,
        leaderboard=leaderboard,
        plan=plan,
        submitted_orders=submitted_orders,
    )


def apply_kill_switch(
    state: LoopState,
    broker: BrokerProtocol,
    bus: EventBus,
    store: SQLiteStore,
    run_id: str,
    reason: str,
) -> LoopState:
    cancelled_order_count = broker.cancel_open_orders()
    killed = state.kill(reason)
    _emit(
        bus,
        store,
        _event(
            run_id,
            EventType.SYSTEM_KILL_SWITCH,
            severity=EventSeverity.CRITICAL,
            payload={"reason": reason, "cancelled_order_count": cancelled_order_count},
        ),
    )
    return killed


def _risk_limits(settings: Settings) -> RiskLimits:
    return RiskLimits(
        max_positions=settings.max_positions,
        max_position_pct=settings.max_position_pct,
        cash_buffer_pct=settings.cash_buffer_pct,
        max_drawdown_pct=settings.max_drawdown_pct,
        min_validation_sharpe=settings.min_validation_sharpe,
    )


def _approved_leaderboard(
    leaderboard: pd.DataFrame,
    candidate_reviews: list[CandidateDecision],
) -> pd.DataFrame:
    if leaderboard.empty or not candidate_reviews:
        return leaderboard.iloc[0:0].copy()
    approved_keys = {
        (review.symbol, review.strategy, review.params)
        for review in candidate_reviews
        if review.risk_decision in {RiskDecision.APPROVED, RiskDecision.RESIZED}
    }
    multipliers = {
        (review.symbol, review.strategy, review.params): review.size_multiplier
        for review in candidate_reviews
        if review.risk_decision in {RiskDecision.APPROVED, RiskDecision.RESIZED}
    }
    if not approved_keys:
        return leaderboard.iloc[0:0].copy()
    approved = leaderboard[
        leaderboard.apply(
            lambda row: (row["symbol"], row["strategy"], row.get("params", "")) in approved_keys,
            axis=1,
        )
    ].copy()
    if approved.empty:
        return approved
    approved["agent_size_multiplier"] = approved.apply(
        lambda row: multipliers[(row["symbol"], row["strategy"], row.get("params", ""))],
        axis=1,
    )
    return approved


def _risk_event(
    run_id: str,
    leaderboard: pd.DataFrame,
    candidate_reviews: list[CandidateDecision],
    plan: TradePlan,
) -> Event:
    if plan.items:
        return _event(
            run_id,
            EventType.RISK_GATE,
            payload={"decision": "approved", "approved_count": len(plan.items)},
        )
    if leaderboard.empty:
        reason = "no_candidates"
    elif candidate_reviews and all(
        review.risk_decision not in {RiskDecision.APPROVED, RiskDecision.RESIZED}
        for review in candidate_reviews
    ):
        reason = "agent_rejected"
    else:
        reason = "risk_rejected"
    return _event(
        run_id,
        EventType.RISK_GATE,
        severity=EventSeverity.WARNING,
        payload={"decision": "blocked", "reason": reason},
    )


def _decision_to_dict(decision: CandidateDecision) -> dict[str, object]:
    return {
        "symbol": decision.symbol,
        "strategy": decision.strategy,
        "risk_decision": decision.risk_decision.value,
        "risk_reason": decision.risk_reason,
        "bull_case": decision.bull_case,
        "bear_case": decision.bear_case,
        "portfolio_decision": decision.portfolio_decision,
        "params": decision.params,
        "size_multiplier": decision.size_multiplier,
        "tool_names": list(decision.tool_names),
    }


def _event(
    run_id: str,
    event_type: EventType,
    severity: EventSeverity = EventSeverity.INFO,
    payload: dict[str, object] | None = None,
) -> Event:
    return Event(
        event_id=f"evt-{uuid4()}",
        run_id=run_id,
        ts=datetime.now(UTC),
        type=event_type,
        severity=severity,
        payload=payload or {},
    )


def _emit(bus: EventBus, store: SQLiteStore, event: Event) -> None:
    store.append_event(event)
    bus.publish(event)