from typing import Any

from pydantic import BaseModel, Field


class ModeStatus(BaseModel):
    mode: str
    execution_enabled: bool = False


class HealthResponse(BaseModel):
    status: str = "ok"
    mode: str
    execution_enabled: bool = False


class AccountSnapshotResponse(ModeStatus):
    snapshot: dict[str, Any] = Field(default_factory=dict)


class PositionsResponse(ModeStatus):
    positions: list[dict[str, Any]] = Field(default_factory=list)


class OrdersResponse(ModeStatus):
    orders: list[dict[str, Any]] = Field(default_factory=list)


class FillsResponse(ModeStatus):
    fills: list[dict[str, Any]] = Field(default_factory=list)


class RiskStatusResponse(ModeStatus):
    risk: dict[str, Any] = Field(default_factory=dict)


class RunsResponse(ModeStatus):
    runs: list[dict[str, Any]] = Field(default_factory=list)


class RunResponse(ModeStatus):
    run: dict[str, Any]
    events: list[dict[str, Any]] = Field(default_factory=list)


class LeaderboardResponse(ModeStatus):
    plan: dict[str, Any]


class ResearchArtifactsResponse(ModeStatus):
    artifacts: dict[str, Any] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)


class TraceResponse(ModeStatus):
    trace: list[dict[str, Any]] = Field(default_factory=list)


class ControlRequest(BaseModel):
    reason: str = "operator"


class PaperExecuteRequest(BaseModel):
    paper_only: bool = False
    confirmation_token: str | None = None


class ControlResponse(ModeStatus):
    state: dict[str, Any]