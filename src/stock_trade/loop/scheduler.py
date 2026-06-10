from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pandas as pd

from stock_trade.agents.protocols import CommitteeProtocol
from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.loop.ralph import BrokerProtocol, RalphRunResult, run_cycle
from stock_trade.loop.state import LoopMode, LoopState
from stock_trade.store.sqlite import SQLiteStore

Clock = Callable[[], datetime]


@dataclass(frozen=True)
class SchedulerTickResult:
    ran: bool
    run_result: RalphRunResult | None = None
    skip_reason: str | None = None


class RalphScheduler:
    def __init__(
        self,
        interval: timedelta,
        clock: Clock | None = None,
        state: LoopState | None = None,
    ) -> None:
        self.interval = interval
        self.clock = clock or (lambda: datetime.now(UTC))
        self.state = state or LoopState(mode=LoopMode.RESEARCH)
        self._next_run_at: datetime | None = None
        self._event_sequence = 0

    def tick(
        self,
        settings: Settings,
        bus: EventBus,
        store: SQLiteStore,
        prices: pd.DataFrame,
        broker: BrokerProtocol | None = None,
        committee: CommitteeProtocol | None = None,
        execute: bool = False,
    ) -> SchedulerTickResult:
        now = self.clock()
        if self.state.mode in {LoopMode.PAUSED, LoopMode.BLOCKED, LoopMode.KILLED}:
            reason = self.state.mode.value
            self._emit_scheduler_event(bus, store, reason, now)
            return SchedulerTickResult(ran=False, skip_reason=reason)

        if self._next_run_at is not None and now < self._next_run_at:
            self._emit_scheduler_event(bus, store, "not_due", now)
            return SchedulerTickResult(ran=False, skip_reason="not_due")

        run_result = run_cycle(
            settings=settings,
            bus=bus,
            store=store,
            prices=prices,
            committee=committee,
            broker=broker,
            loop_state=self.state,
            execute=execute,
        )
        self._next_run_at = now + self.interval
        self._emit_scheduler_event(bus, store, "ran", now, run_id=run_result.run_id)
        return SchedulerTickResult(ran=True, run_result=run_result)

    def _emit_scheduler_event(
        self,
        bus: EventBus,
        store: SQLiteStore,
        reason: str,
        now: datetime,
        run_id: str = "scheduler",
    ) -> None:
        if run_id == "scheduler":
            store.create_run(run_id, mode=self.state.mode.value, status="scheduler")
        self._event_sequence += 1
        event = Event(
            event_id=f"scheduler-{self._event_sequence}-{now.timestamp()}-{reason}",
            run_id=run_id,
            ts=now,
            type=EventType.METRIC_UPDATE,
            severity=EventSeverity.INFO,
            payload={"component": "scheduler", "state": self.state.mode.value, "result": reason},
        )
        store.append_event(event)
        bus.publish(event)