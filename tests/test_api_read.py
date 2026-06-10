from datetime import UTC, datetime

from fastapi.testclient import TestClient

from stock_trade.api.app import create_app
from stock_trade.config import Settings
from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.store.sqlite import SQLiteStore


class FakeBrokerSnapshot:
    def account_snapshot(self):
        return {"equity": 100_000, "cash": 75_000, "mode": "paper"}

    def positions(self):
        return [{"symbol": "SPY", "market_value": 25_000}]

    def open_orders(self):
        return []

    def recent_fills(self):
        return []


def _seed_store(store: SQLiteStore) -> None:
    store.create_run("run-1", mode="paper", status="planned", metadata={"source": "test"})
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
    store.save_plan("run-1", {"items": [{"symbol": "SPY"}]})
    store.save_agent_trace("run-1", "committee", {"decision": "approved"})


def test_api_read_endpoints_return_dashboard_state(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    _seed_store(store)
    client = TestClient(
        create_app(
            settings=Settings(trading_mode="paper", alpaca_api_secret="raw-secret"),
            store=store,
            broker_snapshot=FakeBrokerSnapshot(),
        )
    )

    health = client.get("/health").json()
    assert health["status"] == "ok"
    assert health["execution_enabled"] is False
    assert client.get("/api/account/snapshot").json()["mode"] == "paper"
    assert client.get("/api/positions").json()["positions"][0]["symbol"] == "SPY"
    assert client.get("/api/orders/open").json()["orders"] == []
    assert client.get("/api/fills/recent").json()["fills"] == []
    assert client.get("/api/risk/status").json()["mode"] == "paper"
    assert client.get("/api/research/runs").json()["runs"][0]["run_id"] == "run-1"
    assert client.get("/api/research/runs/run-1").json()["run"]["metadata"] == {"source": "test"}
    assert client.get("/api/research/runs/run-1/leaderboard").json()["plan"]["items"]
    assert client.get("/api/agent/runs/run-1/trace").json()["trace"][0]["agent_name"] == "committee"


def test_api_trace_endpoint_returns_404_for_unknown_run(tmp_path) -> None:
    client = TestClient(create_app(settings=Settings(), store=SQLiteStore(tmp_path / "ralph.db")))

    response = client.get("/api/agent/runs/missing/trace")

    assert response.status_code == 404


def test_api_responses_do_not_serialize_secrets(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    _seed_store(store)
    client = TestClient(
        create_app(
            settings=Settings(trading_mode="paper", alpaca_api_secret="raw-secret"),
            store=store,
            broker_snapshot=FakeBrokerSnapshot(),
        )
    )

    for path in [
        "/health",
        "/api/account/snapshot",
        "/api/risk/status",
        "/api/research/runs",
        "/api/agent/runs/run-1/trace",
    ]:
        assert "raw-secret" not in client.get(path).text