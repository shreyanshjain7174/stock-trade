from datetime import UTC, datetime, timedelta

import pandas as pd

from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.events.models import EventType
from stock_trade.loop.scheduler import RalphScheduler
from stock_trade.loop.state import LoopMode, LoopState
from stock_trade.store.sqlite import SQLiteStore


class MutableClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class FakeBroker:
    def __init__(self) -> None:
        self.submitted = False

    def submit_buy_plan(self, plan):
        self.submitted = True
        return []

    def cancel_open_orders(self) -> int:
        return 0


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {"SPY": [100 + index * 0.20 for index in range(620)]},
        index=pd.date_range("2020-01-01", periods=620, freq="D"),
    )


def _paper_settings() -> Settings:
    return Settings(
        trading_mode="paper",
        allow_paper_orders=True,
        alpaca_api_key="paper-key",
        alpaca_api_secret="paper-secret",
        min_validation_sharpe=0.10,
    )


def test_scheduler_runs_when_due_then_waits_for_interval(tmp_path) -> None:
    clock = MutableClock(datetime(2026, 6, 2, tzinfo=UTC))
    scheduler = RalphScheduler(interval=timedelta(minutes=5), clock=clock)
    store = SQLiteStore(tmp_path / "ralph.db")

    first = scheduler.tick(
        settings=_paper_settings(),
        bus=EventBus(),
        store=store,
        prices=_prices(),
        broker=FakeBroker(),
    )
    second = scheduler.tick(
        settings=_paper_settings(),
        bus=EventBus(),
        store=store,
        prices=_prices(),
        broker=FakeBroker(),
    )
    clock.advance(timedelta(minutes=5))
    third = scheduler.tick(
        settings=_paper_settings(),
        bus=EventBus(),
        store=store,
        prices=_prices(),
        broker=FakeBroker(),
    )

    assert first.ran is True
    assert second.ran is False
    assert second.skip_reason == "not_due"
    assert third.ran is True


def test_scheduler_skips_while_paused_and_resumes_cleanly(tmp_path) -> None:
    scheduler = RalphScheduler(
        interval=timedelta(minutes=5),
        clock=lambda: datetime(2026, 6, 2, tzinfo=UTC),
        state=LoopState(mode=LoopMode.PAUSED),
    )
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    skipped = scheduler.tick(
        settings=_paper_settings(),
        bus=bus,
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=FakeBroker(),
    )
    scheduler.state = LoopState(mode=LoopMode.PAPER)
    ran = scheduler.tick(
        settings=_paper_settings(),
        bus=bus,
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=FakeBroker(),
    )

    assert skipped.ran is False
    assert skipped.skip_reason == "paused"
    assert ran.ran is True
    assert EventType.METRIC_UPDATE in [event.type for event in seen]


def test_scheduler_never_executes_broker_in_research_mode(tmp_path) -> None:
    broker = FakeBroker()
    scheduler = RalphScheduler(
        interval=timedelta(minutes=5),
        clock=lambda: datetime(2026, 6, 2, tzinfo=UTC),
        state=LoopState(mode=LoopMode.RESEARCH),
    )

    result = scheduler.tick(
        settings=Settings(min_validation_sharpe=0.10),
        bus=EventBus(),
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=broker,
        execute=True,
    )

    assert result.ran is True
    assert broker.submitted is False


def test_scheduler_persists_repeated_skips_with_same_clock(tmp_path) -> None:
    fixed_now = datetime(2026, 6, 2, tzinfo=UTC)
    scheduler = RalphScheduler(
        interval=timedelta(minutes=5),
        clock=lambda: fixed_now,
        state=LoopState(mode=LoopMode.PAUSED),
    )
    store = SQLiteStore(tmp_path / "ralph.db")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    scheduler.tick(settings=_paper_settings(), bus=bus, store=store, prices=_prices())
    scheduler.tick(settings=_paper_settings(), bus=bus, store=store, prices=_prices())

    assert len(seen) == 2
    assert len(store.list_events("scheduler")) == 2