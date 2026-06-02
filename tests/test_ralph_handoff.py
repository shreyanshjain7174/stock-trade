import pandas as pd

from stock_trade.brokers.alpaca_paper import SubmittedOrder
from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.events.models import EventType
from stock_trade.loop.ralph import apply_kill_switch, run_cycle
from stock_trade.loop.state import LoopMode, LoopState
from stock_trade.store.sqlite import SQLiteStore


class FakeBroker:
    def __init__(self) -> None:
        self.submitted = False
        self.cancelled = False

    def submit_buy_plan(self, plan):
        self.submitted = True
        return [SubmittedOrder("SPY", "buy", 1000, "order-1")]

    def cancel_open_orders(self) -> int:
        self.cancelled = True
        return 2


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


def test_ralph_cycle_default_does_not_execute_broker(tmp_path) -> None:
    broker = FakeBroker()

    run_cycle(
        settings=_paper_settings(),
        bus=EventBus(),
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=broker,
    )

    assert broker.submitted is False


def test_ralph_cycle_execute_submits_only_when_state_allows(tmp_path) -> None:
    broker = FakeBroker()
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    result = run_cycle(
        settings=_paper_settings(),
        bus=bus,
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=broker,
        loop_state=LoopState(mode=LoopMode.PAPER),
        execute=True,
    )

    assert broker.submitted is True
    assert result.submitted_orders
    assert EventType.BROKER_ORDER in [event.type for event in seen]


def test_ralph_cycle_execute_refuses_when_state_paused(tmp_path) -> None:
    broker = FakeBroker()

    result = run_cycle(
        settings=_paper_settings(),
        bus=EventBus(),
        store=SQLiteStore(tmp_path / "ralph.db"),
        prices=_prices(),
        broker=broker,
        loop_state=LoopState(mode=LoopMode.PAUSED),
        execute=True,
    )

    assert broker.submitted is False
    assert result.submitted_orders == []


def test_kill_switch_cancels_orders_and_blocks_future_execution(tmp_path) -> None:
    broker = FakeBroker()
    store = SQLiteStore(tmp_path / "ralph.db")
    store.create_run("run-1", mode="paper", status="started")
    bus = EventBus()
    seen = []
    bus.subscribe(seen.append)

    killed = apply_kill_switch(
        state=LoopState(mode=LoopMode.PAPER),
        broker=broker,
        bus=bus,
        store=store,
        run_id="run-1",
        reason="operator",
    )

    assert broker.cancelled is True
    assert killed.can_execute is False
    assert killed.mode is LoopMode.KILLED
    assert seen[-1].type is EventType.SYSTEM_KILL_SWITCH
    assert seen[-1].payload["cancelled_order_count"] == 2