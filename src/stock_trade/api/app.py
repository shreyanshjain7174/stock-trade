from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from stock_trade.api.schemas import (
    AccountSnapshotResponse,
    ControlRequest,
    ControlResponse,
    FillsResponse,
    HealthResponse,
    LeaderboardResponse,
    OrdersResponse,
    PaperExecuteRequest,
    PositionsResponse,
    RiskStatusResponse,
    RunResponse,
    RunsResponse,
    TraceResponse,
)
from stock_trade.config import Settings, get_settings
from stock_trade.events.models import Event, EventSeverity, EventType
from stock_trade.loop.state import LoopMode, LoopState
from stock_trade.store.sqlite import SQLiteStore


class BrokerSnapshotProtocol(Protocol):
    def account_snapshot(self) -> dict[str, Any]:
        pass

    def positions(self) -> list[dict[str, Any]]:
        pass

    def open_orders(self) -> list[dict[str, Any]]:
        pass

    def recent_fills(self) -> list[dict[str, Any]]:
        pass

    def cancel_open_orders(self) -> int:
        pass


class PaperExecutorProtocol(Protocol):
    def execute_paper(self) -> dict[str, object]:
        pass


class EmptyBrokerSnapshot:
    def account_snapshot(self) -> dict[str, Any]:
        return {}

    def positions(self) -> list[dict[str, Any]]:
        return []

    def open_orders(self) -> list[dict[str, Any]]:
        return []

    def recent_fills(self) -> list[dict[str, Any]]:
        return []

    def cancel_open_orders(self) -> int:
        return 0


def create_app(
    settings: Settings | None = None,
    store: SQLiteStore | None = None,
    broker_snapshot: BrokerSnapshotProtocol | None = None,
    paper_executor: PaperExecutorProtocol | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app_store = store or SQLiteStore(app_settings_path())
    broker = broker_snapshot or EmptyBrokerSnapshot()
    initial_mode = LoopMode.PAPER if app_settings.trading_mode == "paper" else LoopMode.RESEARCH
    state = {"value": LoopState(mode=initial_mode)}
    app = FastAPI(title="stock-trade dashboard API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
        )

    @app.get("/api/account/snapshot", response_model=AccountSnapshotResponse)
    def account_snapshot() -> AccountSnapshotResponse:
        snapshot = broker.account_snapshot()
        return AccountSnapshotResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            snapshot=snapshot,
        )

    @app.get("/api/positions", response_model=PositionsResponse)
    def positions() -> PositionsResponse:
        return PositionsResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            positions=broker.positions(),
        )

    @app.get("/api/orders/open", response_model=OrdersResponse)
    def open_orders() -> OrdersResponse:
        return OrdersResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            orders=broker.open_orders(),
        )

    @app.get("/api/fills/recent", response_model=FillsResponse)
    def recent_fills() -> FillsResponse:
        return FillsResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            fills=broker.recent_fills(),
        )

    @app.get("/api/risk/status", response_model=RiskStatusResponse)
    def risk_status() -> RiskStatusResponse:
        return RiskStatusResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            risk={
                "max_positions": app_settings.max_positions,
                "max_position_pct": app_settings.max_position_pct,
                "cash_buffer_pct": app_settings.cash_buffer_pct,
                "max_drawdown_pct": app_settings.max_drawdown_pct,
                "min_validation_sharpe": app_settings.min_validation_sharpe,
            },
        )

    @app.get("/api/research/runs", response_model=RunsResponse)
    def research_runs() -> RunsResponse:
        return RunsResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            runs=app_store.list_runs(),
        )

    @app.get("/api/research/runs/{run_id}", response_model=RunResponse)
    def research_run(run_id: str) -> RunResponse:
        try:
            run = app_store.get_run(run_id)
            events = [event.to_dict() for event in app_store.list_events(run_id)]
        except KeyError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        return RunResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            run=run,
            events=events,
        )

    @app.get("/api/research/runs/{run_id}/leaderboard", response_model=LeaderboardResponse)
    def research_leaderboard(run_id: str) -> LeaderboardResponse:
        try:
            plan = app_store.get_plan(run_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="plan not found") from error
        return LeaderboardResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            plan=plan,
        )

    @app.get("/api/agent/runs/{run_id}/trace", response_model=TraceResponse)
    def agent_trace(run_id: str) -> TraceResponse:
        try:
            app_store.get_run(run_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        return TraceResponse(
            mode=app_settings.trading_mode,
            execution_enabled=_execution_enabled(app_settings),
            trace=app_store.get_trace(run_id),
        )

    @app.get("/api/events/stream")
    def event_stream(run_id: str | None = None) -> StreamingResponse:
        def stream_events():
            for event in app_store.iter_all_events(run_id=run_id):
                yield f"event: {event.type.value}\n"
                yield f"data: {event.to_json()}\n\n"

        return StreamingResponse(stream_events(), media_type="text/event-stream")

    @app.post("/api/system/pause", response_model=ControlResponse)
    def pause(request: ControlRequest) -> ControlResponse:
        state["value"] = state["value"].pause(request.reason)
        _audit_control(app_store, "pause", request.reason, state["value"])
        return _control_response(app_settings, state["value"])

    @app.post("/api/system/resume", response_model=ControlResponse)
    def resume(request: ControlRequest) -> ControlResponse:
        state["value"] = state["value"].resume(request.reason)
        _audit_control(app_store, "resume", request.reason, state["value"])
        return _control_response(app_settings, state["value"])

    @app.post("/api/system/kill-switch", response_model=ControlResponse)
    def kill_switch(request: ControlRequest) -> ControlResponse:
        cancelled_order_count = broker.cancel_open_orders()
        state["value"] = state["value"].kill(request.reason)
        _audit_control(
            app_store,
            "kill-switch",
            request.reason,
            state["value"],
            EventSeverity.CRITICAL,
            {"cancelled_order_count": cancelled_order_count},
        )
        return _control_response(
            app_settings,
            state["value"],
            {"cancelled_order_count": cancelled_order_count},
        )

    @app.post("/api/paper/execute", response_model=ControlResponse)
    def paper_execute(request: PaperExecuteRequest) -> ControlResponse:
        if not request.paper_only or request.confirmation_token != "execute-paper":
            raise HTTPException(status_code=403, detail="paper execution confirmation required")
        if not _execution_enabled(app_settings):
            raise HTTPException(status_code=403, detail="paper execution gates are not enabled")
        if not state["value"].can_execute:
            _audit_control(
                app_store,
                "paper-execute-blocked",
                "loop state does not allow paper execution",
                state["value"],
            )
            raise HTTPException(status_code=409, detail="loop state does not allow paper execution")
        if paper_executor is None:
            _audit_control(
                app_store,
                "paper-execute-blocked",
                "executor unavailable",
                state["value"],
            )
            raise HTTPException(status_code=501, detail="paper execution endpoint is not wired")
        execution_result = paper_executor.execute_paper()
        _audit_control(
            app_store,
            "paper-execute",
            "confirmed",
            state["value"],
            extra=execution_result,
        )
        return _control_response(app_settings, state["value"], execution_result)

    return app


def app_settings_path():
    from pathlib import Path

    return Path("artifacts/ralph.db")


def _execution_enabled(settings: Settings) -> bool:
    return bool(
        settings.trading_mode == "paper"
        and settings.allow_paper_orders
        and settings.alpaca_api_key is not None
        and settings.alpaca_api_secret is not None
    )


def _control_response(
    settings: Settings,
    state: LoopState,
    extra_state: dict[str, object] | None = None,
) -> ControlResponse:
    return ControlResponse(
        mode=settings.trading_mode,
        execution_enabled=_execution_enabled(settings),
        state={"mode": state.mode.value, "reason": state.reason, **(extra_state or {})},
    )


def _audit_control(
    store: SQLiteStore,
    action: str,
    reason: str,
    state: LoopState,
    severity: EventSeverity = EventSeverity.INFO,
    extra: dict[str, object] | None = None,
) -> None:
    run_id = "api-controls"
    store.create_run(run_id, mode=state.mode.value, status="control")
    store.append_event(
        Event(
            event_id=f"api-control-{uuid4()}",
            run_id=run_id,
            ts=datetime.now(UTC),
            type=EventType.METRIC_UPDATE,
            severity=severity,
            payload={"component": "api", "action": action, "reason": reason, **(extra or {})},
        )
    )