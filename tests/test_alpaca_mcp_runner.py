import importlib.util
from pathlib import Path


def _load_runner_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_alpaca_mcp.py"
    spec = importlib.util.spec_from_file_location("run_alpaca_mcp", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_show_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "show_alpaca_account_clock_mcp.py"
    )
    spec = importlib.util.spec_from_file_location("show_alpaca_account_clock_mcp", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_overrides_inherited_mcp_safety_env(monkeypatch) -> None:
    module = _load_runner_module()
    captured: dict[str, object] = {}

    monkeypatch.setenv("ALPACA_API_KEY", "env-key")
    monkeypatch.setenv("ALPACA_API_SECRET", "env-secret")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "env-secret-key")
    monkeypatch.setenv("ALPACA_PAPER_TRADE", "false")
    monkeypatch.setenv("ALPACA_TOOLSETS", "trading,account")
    monkeypatch.setattr(module, "dotenv_values", lambda _path: {})

    def fake_call(command, env):
        captured["command"] = command
        captured["env"] = env
        return 0

    monkeypatch.setattr(module.subprocess, "call", fake_call)

    assert module.main() == 0

    env = captured["env"]
    assert captured["command"] == ["uvx", "alpaca-mcp-server"]
    assert env["ALPACA_PAPER_TRADE"] == "true"
    assert env["ALPACA_TOOLSETS"] == "assets,stock-data,news,corporate-actions"
    assert env["ALPACA_API_KEY"] == "env-key"
    assert env["ALPACA_SECRET_KEY"] == "env-secret"
    assert "ALPACA_API_SECRET" not in env


def test_runner_accepts_alpaca_api_secret_from_environment(monkeypatch) -> None:
    module = _load_runner_module()
    captured: dict[str, object] = {}

    monkeypatch.setenv("ALPACA_API_KEY", "env-key")
    monkeypatch.setenv("ALPACA_API_SECRET", "env-secret")
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setattr(module, "dotenv_values", lambda _path: {})

    def fake_call(command, env):
        captured["command"] = command
        captured["env"] = env
        return 0

    monkeypatch.setattr(module.subprocess, "call", fake_call)

    assert module.main() == 0

    env = captured["env"]
    assert env["ALPACA_SECRET_KEY"] == "env-secret"
    assert "ALPACA_API_SECRET" not in env


def test_show_helper_accepts_alpaca_api_secret_from_environment(monkeypatch) -> None:
    module = _load_show_module()

    monkeypatch.setenv("ALPACA_API_KEY", "env-key")
    monkeypatch.setenv("ALPACA_API_SECRET", "env-secret")
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.setenv("ALPACA_PAPER_TRADE", "false")
    monkeypatch.setenv("ALPACA_TOOLSETS", "trading,account")
    monkeypatch.setattr(module, "dotenv_values", lambda _path: {})

    env = module._mcp_env()

    assert env["ALPACA_API_KEY"] == "env-key"
    assert env["ALPACA_SECRET_KEY"] == "env-secret"
    assert env["ALPACA_PAPER_TRADE"] == "true"
    assert env["ALPACA_TOOLSETS"] == module.READ_ONLY_TOOLSETS
    assert "ALPACA_API_SECRET" not in env