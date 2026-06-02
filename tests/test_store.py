import sqlite3
from datetime import UTC, datetime

import pytest

from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.store.sqlite import SQLiteStore


def _event(event_id: str) -> Event:
    return Event(
        event_id=event_id,
        run_id="run-1",
        ts=datetime(2026, 6, 2, tzinfo=UTC),
        type=EventType.PLAN_CREATED,
        severity=EventSeverity.INFO,
        symbol="SPY",
        payload={"target_weight": 0.25},
    )


def test_sqlite_store_persists_run_events_plan_and_trace(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    store.create_run("run-1", mode="paper", status="planned", metadata={"source": "test"})
    store.append_event(_event("evt-1"))
    store.save_plan("run-1", {"items": [{"symbol": "SPY"}]})
    store.save_agent_trace("run-1", "risk_manager", {"decision": "approved"})

    assert store.get_run("run-1")["metadata"] == {"source": "test"}
    assert [event.event_id for event in store.list_events("run-1")] == ["evt-1"]
    assert store.get_plan("run-1") == {"items": [{"symbol": "SPY"}]}
    assert store.get_trace("run-1") == [
        {"agent_name": "risk_manager", "trace": {"decision": "approved"}}
    ]


def test_sqlite_store_writes_are_idempotent(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    store.create_run("run-1", mode="paper", status="planned")
    store.create_run("run-1", mode="paper", status="planned")
    store.append_event(_event("evt-1"))
    store.append_event(_event("evt-1"))

    assert len(store.list_runs()) == 1
    assert len(store.list_events("run-1")) == 1


def test_sqlite_store_updates_existing_run_status(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    store.create_run("run-1", mode="paper", status="started")
    store.create_run("run-1", mode="paper", status="planned")

    assert len(store.list_runs()) == 1
    assert store.get_run("run-1")["status"] == "planned"


def test_sqlite_store_preserves_metadata_when_status_updates_without_metadata(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    store.create_run("run-1", mode="paper", status="started", metadata={"source": "agent"})
    store.create_run("run-1", mode="paper", status="planned")

    run = store.get_run("run-1")

    assert run["status"] == "planned"
    assert run["metadata"] == {"source": "agent"}


def test_sqlite_store_rejects_events_for_missing_run(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    with pytest.raises(sqlite3.IntegrityError):
        store.append_event(_event("evt-1"))


def test_sqlite_store_returns_events_in_insert_order_for_same_timestamp(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    store.create_run("run-1", mode="paper", status="planned")

    store.append_event(_event("evt-b"))
    store.append_event(_event("evt-a"))

    assert [event.event_id for event in store.list_events("run-1")] == ["evt-b", "evt-a"]


def test_sqlite_store_agent_traces_are_append_only(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    store.create_run("run-1", mode="paper", status="planned")

    store.save_agent_trace("run-1", "risk_manager", {"decision": "approved"})
    store.save_agent_trace("run-1", "risk_manager", {"decision": "approved"})

    assert len(store.get_trace("run-1")) == 2


def test_sqlite_store_uses_wal_mode(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")

    assert store.journal_mode() == "wal"