from datetime import UTC, datetime

import pytest

from stock_trade.events.models import Event, EventSeverity, EventType


def test_event_round_trips_json() -> None:
    event = Event(
        event_id="evt-1",
        run_id="run-1",
        ts=datetime(2026, 6, 2, tzinfo=UTC),
        type=EventType.RISK_GATE,
        severity=EventSeverity.WARNING,
        symbol="SPY",
        payload={"decision": "resized"},
    )

    restored = Event.from_json(event.to_json())

    assert restored == event
    assert restored.to_dict()["type"] == "risk.gate"
    assert restored.to_dict()["severity"] == "warning"


def test_event_rejects_invalid_type_and_severity() -> None:
    valid_payload = {
        "event_id": "evt-1",
        "run_id": "run-1",
        "ts": "2026-06-02T00:00:00+00:00",
        "type": "risk.gate",
        "severity": "info",
        "symbol": None,
        "payload": {},
    }

    with pytest.raises(ValueError):
        Event.from_dict({**valid_payload, "type": "bad.type"})
    with pytest.raises(ValueError):
        Event.from_dict({**valid_payload, "severity": "bad"})


def test_event_payload_is_immutable_from_callers() -> None:
    payload = {"decision": "approved"}
    event = Event(
        event_id="evt-1",
        run_id="run-1",
        ts=datetime(2026, 6, 2, tzinfo=UTC),
        type=EventType.RISK_GATE,
        severity=EventSeverity.INFO,
        payload=payload,
    )

    payload["decision"] = "blocked"

    with pytest.raises(TypeError):
        event.payload["decision"] = "resized"
    assert event.to_dict()["payload"] == {"decision": "approved"}