from datetime import UTC, datetime

from fastapi.testclient import TestClient

from stock_trade.api.app import create_app
from stock_trade.config import Settings
from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.store.sqlite import SQLiteStore


def test_api_event_stream_returns_sse_events(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    store.create_run("run-1", mode="paper", status="planned")
    store.append_event(
        Event(
            event_id="evt-1",
            run_id="run-1",
            ts=datetime(2026, 6, 2, tzinfo=UTC),
            type=EventType.PLAN_CREATED,
            severity=EventSeverity.INFO,
            payload={"item_count": 1},
        )
    )
    client = TestClient(create_app(settings=Settings(), store=store))

    response = client.get("/api/events/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: plan.created" in response.text
    assert "data:" in response.text
    assert "evt-1" in response.text