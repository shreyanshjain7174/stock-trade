from fastapi.testclient import TestClient

from stock_trade.api.app import create_app
from stock_trade.config import Settings
from stock_trade.store.sqlite import SQLiteStore


class ControlBroker:
    def __init__(self) -> None:
        self.cancelled = False

    def account_snapshot(self):
        return {}

    def positions(self):
        return []

    def open_orders(self):
        return []

    def recent_fills(self):
        return []

    def cancel_open_orders(self) -> int:
        self.cancelled = True
        return 2


class FailingCancelBroker(ControlBroker):
    def cancel_open_orders(self) -> int:
        self.cancelled = True
        raise RuntimeError("broker unavailable")


class PaperExecutor:
    def __init__(self) -> None:
        self.call_count = 0

    def execute_paper(self) -> dict[str, object]:
        self.call_count += 1
        return {"submitted_order_count": 1}


def test_api_pause_resume_and_kill_switch_controls(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    broker = ControlBroker()
    client = TestClient(create_app(settings=Settings(), store=store, broker_snapshot=broker))

    pause = client.post("/api/system/pause", json={"reason": "operator"})
    resume = client.post("/api/system/resume", json={"reason": "operator"})
    kill = client.post("/api/system/kill-switch", json={"reason": "operator"})

    assert pause.status_code == 200
    assert pause.json()["state"]["mode"] == "paused"
    assert resume.status_code == 200
    assert resume.json()["state"]["mode"] == "research"
    assert kill.status_code == 200
    assert kill.json()["state"]["mode"] == "killed"
    assert kill.json()["state"]["cancelled_order_count"] == 2
    assert broker.cancelled is True


def test_api_paper_execute_requires_paper_only_and_confirmation(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(create_app(settings=Settings(trading_mode="paper"), store=store))

    assert client.post("/api/paper/execute", json={"paper_only": False}).status_code == 403
    assert client.post("/api/paper/execute", json={"paper_only": True}).status_code == 403
    assert (
        client.post(
            "/api/paper/execute",
            json={"paper_only": True, "confirmation_token": "execute-paper"},
        ).status_code
        == 403
    )


def test_api_paper_execute_does_not_report_success_without_executor(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(
        create_app(
            settings=Settings(
                trading_mode="paper",
                allow_paper_orders=True,
                alpaca_api_key="paper-key",
                alpaca_api_secret="paper-secret",
            ),
            store=store,
        )
    )

    response = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )

    assert response.status_code == 501


def test_api_paper_execute_calls_injected_executor(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    executor = PaperExecutor()
    client = TestClient(
        create_app(
            settings=Settings(
                trading_mode="paper",
                allow_paper_orders=True,
                alpaca_api_key="paper-key",
                alpaca_api_secret="paper-secret",
            ),
            store=store,
            paper_executor=executor,
        )
    )

    response = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )

    assert response.status_code == 200
    assert response.json()["state"]["submitted_order_count"] == 1
    assert executor.call_count == 1


def test_api_paper_execute_refuses_after_pause_or_kill_switch(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    executor = PaperExecutor()
    client = TestClient(
        create_app(
            settings=Settings(
                trading_mode="paper",
                allow_paper_orders=True,
                alpaca_api_key="paper-key",
                alpaca_api_secret="paper-secret",
            ),
            store=store,
            paper_executor=executor,
        )
    )

    assert client.post("/api/system/pause", json={"reason": "operator"}).status_code == 200
    paused_execute = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )
    assert paused_execute.status_code == 409

    assert client.post("/api/system/resume", json={"reason": "operator"}).status_code == 200
    allowed_execute = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )
    assert allowed_execute.status_code == 200

    assert client.post("/api/system/kill-switch", json={"reason": "operator"}).status_code == 200
    killed_execute = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )
    assert killed_execute.status_code == 409
    assert executor.call_count == 1


def test_api_health_reports_loop_state_and_execution_disabled_after_controls(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(
        create_app(
            settings=Settings(
                trading_mode="paper",
                allow_paper_orders=True,
                alpaca_api_key="paper-key",
                alpaca_api_secret="paper-secret",
            ),
            store=store,
        )
    )

    assert client.get("/health").json()["mode"] == "paper"

    paused = client.post("/api/system/pause", json={"reason": "operator"})
    health = client.get("/health")

    assert paused.status_code == 200
    assert health.json()["mode"] == "paused"
    assert health.json()["execution_enabled"] is False


def test_api_kill_switch_latches_killed_before_cancel_error(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    executor = PaperExecutor()
    broker = FailingCancelBroker()
    client = TestClient(
        create_app(
            settings=Settings(
                trading_mode="paper",
                allow_paper_orders=True,
                alpaca_api_key="paper-key",
                alpaca_api_secret="paper-secret",
            ),
            store=store,
            broker_snapshot=broker,
            paper_executor=executor,
        )
    )

    kill = client.post("/api/system/kill-switch", json={"reason": "operator"})
    execute = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )
    health = client.get("/health")

    assert kill.status_code == 502
    assert broker.cancelled is True
    assert execute.status_code == 409
    assert executor.call_count == 0
    assert health.json()["mode"] == "killed"
    assert health.json()["execution_enabled"] is False


def test_api_controls_emit_audit_events(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(create_app(settings=Settings(), store=store))

    client.post("/api/system/pause", json={"reason": "operator"})

    events = store.list_events("api-controls")

    assert events[-1].payload["action"] == "pause"
    assert events[-1].payload["reason"] == "operator"