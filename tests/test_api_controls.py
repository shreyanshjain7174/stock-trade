from fastapi.testclient import TestClient

from stock_trade.api.app import create_app
from stock_trade.config import Settings
from stock_trade.store.sqlite import SQLiteStore


def test_api_pause_resume_and_kill_switch_controls(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(create_app(settings=Settings(), store=store))

    pause = client.post("/api/system/pause", json={"reason": "operator"})
    resume = client.post("/api/system/resume", json={"reason": "operator"})
    kill = client.post("/api/system/kill-switch", json={"reason": "operator"})

    assert pause.status_code == 200
    assert pause.json()["state"]["mode"] == "paused"
    assert resume.status_code == 200
    assert resume.json()["state"]["mode"] == "research"
    assert kill.status_code == 200
    assert kill.json()["state"]["mode"] == "killed"


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


def test_api_controls_emit_audit_events(tmp_path) -> None:
    store = SQLiteStore(tmp_path / "ralph.db")
    client = TestClient(create_app(settings=Settings(), store=store))

    client.post("/api/system/pause", json={"reason": "operator"})

    events = store.list_events("api-controls")

    assert events[-1].payload["action"] == "pause"
    assert events[-1].payload["reason"] == "operator"