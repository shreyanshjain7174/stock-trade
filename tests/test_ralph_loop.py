import pandas as pd

from stock_trade.agents.protocols import CandidateDecision, RiskDecision
from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.events.models import EventType
from stock_trade.loop.ralph import run_cycle
from stock_trade.store.sqlite import SQLiteStore


def _prices(length: int = 620) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SPY": [100 + (index * 0.20) + ((index % 5) * 0.05) for index in range(length)],
            "QQQ": [120 + (index * 0.25) + ((index % 7) * 0.04) for index in range(length)],
        },
        index=pd.date_range("2020-01-01", periods=length, freq="D"),
    )


def test_ralph_cycle_persists_research_risk_and_plan_events(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    result = run_cycle(
        settings=Settings(min_validation_sharpe=0.10),
        bus=bus,
        store=store,
        prices=_prices(),
    )

    event_types = [event.type for event in seen]

    assert result.plan.items
    assert EventType.RESEARCH_STARTED in event_types
    assert EventType.RESEARCH_COMPLETED in event_types
    assert EventType.RISK_GATE in event_types
    assert EventType.PLAN_CREATED in event_types
    assert store.get_run(result.run_id)["status"] == "planned"
    assert store.get_plan(result.run_id)["items"]
    assert [event.event_id for event in store.list_events(result.run_id)] == [
        event.event_id for event in seen
    ]


def test_ralph_cycle_handles_empty_candidates_without_orders(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    result = run_cycle(
        settings=Settings(min_validation_sharpe=0.10),
        bus=bus,
        store=store,
        prices=_prices(length=20),
    )

    risk_events = [event for event in seen if event.type is EventType.RISK_GATE]

    assert result.plan.items == []
    assert risk_events[-1].payload["decision"] == "blocked"
    assert risk_events[-1].payload["reason"] == "no_candidates"


def test_ralph_cycle_distinguishes_risk_rejected_candidates(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    result = run_cycle(
        settings=Settings(min_validation_sharpe=999),
        bus=bus,
        store=store,
        prices=_prices(),
    )

    risk_events = [event for event in seen if event.type is EventType.RISK_GATE]

    assert result.leaderboard.empty is False
    assert result.plan.items == []
    assert risk_events[-1].payload["decision"] == "blocked"
    assert risk_events[-1].payload["reason"] == "risk_rejected"


def test_ralph_cycle_blocks_candidates_rejected_by_committee(tmp_path) -> None:
    class RejectingCommittee:
        def review(self, leaderboard: pd.DataFrame) -> list[CandidateDecision]:
            return [
                CandidateDecision(
                    symbol=str(row.symbol),
                    strategy=str(row.strategy),
                    risk_decision=RiskDecision.REJECTED,
                    risk_reason="committee_rejected",
                    bull_case="none",
                    bear_case="risk too high",
                    portfolio_decision="exclude",
                    params=str(row.params),
                    tool_names=("leaderboard",),
                )
                for row in leaderboard.itertuples(index=False)
            ]

    store = SQLiteStore(tmp_path / "ralph.db")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    result = run_cycle(
        settings=Settings(min_validation_sharpe=0.10),
        bus=bus,
        store=store,
        prices=_prices(),
        committee=RejectingCommittee(),
    )

    risk_events = [event for event in seen if event.type is EventType.RISK_GATE]

    assert EventType.AGENT_TOOL_CALL in [event.type for event in seen]
    assert result.plan.items == []
    assert risk_events[-1].payload["reason"] == "agent_rejected"
    assert store.get_trace(result.run_id)


def test_ralph_cycle_applies_resized_committee_decision(tmp_path) -> None:
    class ResizingCommittee:
        def review(self, leaderboard: pd.DataFrame) -> list[CandidateDecision]:
            return [
                CandidateDecision(
                    symbol=str(row.symbol),
                    strategy=str(row.strategy),
                    risk_decision=RiskDecision.RESIZED,
                    risk_reason="committee_resized",
                    bull_case="some upside",
                    bear_case="size down",
                    portfolio_decision="resize",
                    params=str(row.params),
                    size_multiplier=0.5,
                    tool_names=("leaderboard",),
                )
                for row in leaderboard.itertuples(index=False)
            ]

    result = run_cycle(
        settings=Settings(min_validation_sharpe=0.10),
        bus=EventBus(),
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        committee=ResizingCommittee(),
    )

    assert result.plan.items
    assert max(item.target_weight for item in result.plan.items) <= 0.125


def test_approved_leaderboard_uses_params_to_avoid_duplicate_strategy_leaks() -> None:
    from stock_trade.loop.ralph import _approved_leaderboard

    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "trend",
                "params": '{"fast": 20}',
                "score": 1.0,
            },
            {
                "symbol": "SPY",
                "strategy": "trend",
                "params": '{"fast": 50}',
                "score": 0.9,
            },
        ]
    )
    decisions = [
        CandidateDecision(
            symbol="SPY",
            strategy="trend",
            risk_decision=RiskDecision.APPROVED,
            risk_reason="ok",
            bull_case="ok",
            bear_case="risk",
            portfolio_decision="include",
            params='{"fast": 20}',
        ),
        CandidateDecision(
            symbol="SPY",
            strategy="trend",
            risk_decision=RiskDecision.REJECTED,
            risk_reason="no",
            bull_case="no",
            bear_case="risk",
            portfolio_decision="exclude",
            params='{"fast": 50}',
        ),
    ]

    approved = _approved_leaderboard(leaderboard, decisions)

    assert approved["params"].tolist() == ['{"fast": 20}']