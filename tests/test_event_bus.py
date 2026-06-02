from datetime import UTC, datetime

from stock_trade.events.bus import EventBus, JsonlEventSink
from stock_trade.events.models import Event, EventSeverity, EventType


def _event(event_id: str) -> Event:
    return Event(
        event_id=event_id,
        run_id="run-1",
        ts=datetime(2026, 6, 2, tzinfo=UTC),
        type=EventType.RESEARCH_STARTED,
        severity=EventSeverity.INFO,
        symbol=None,
        payload={},
    )


def test_event_bus_notifies_subscribers_in_order() -> None:
    seen: list[str] = []
    bus = EventBus()
    bus.subscribe(lambda event: seen.append(event.event_id))

    bus.publish(_event("evt-1"))
    bus.publish(_event("evt-2"))

    assert seen == ["evt-1", "evt-2"]


def test_event_bus_continues_after_subscriber_error() -> None:
    seen: list[str] = []
    bus = EventBus()

    def broken_subscriber(event: Event) -> None:
        raise RuntimeError(f"failed {event.event_id}")

    bus.subscribe(broken_subscriber)
    bus.subscribe(lambda event: seen.append(event.event_id))

    try:
        bus.publish(_event("evt-1"))
    except ExceptionGroup as error:
        assert len(error.exceptions) == 1

    assert seen == ["evt-1"]


def test_jsonl_event_sink_appends_events(tmp_path) -> None:
    sink = JsonlEventSink(tmp_path)

    sink(_event("evt-1"))
    sink(_event("evt-2"))

    lines = (tmp_path / "run-1.jsonl").read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert Event.from_json(lines[0]).event_id == "evt-1"
    assert Event.from_json(lines[1]).event_id == "evt-2"