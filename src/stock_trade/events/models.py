from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class EventSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventType(StrEnum):
    RESEARCH_STARTED = "research.started"
    RESEARCH_COMPLETED = "research.completed"
    AGENT_TOOL_CALL = "agent.tool_call"
    RISK_GATE = "risk.gate"
    PLAN_CREATED = "plan.created"
    BROKER_ORDER = "broker.order"
    BROKER_FILL = "broker.fill"
    SYSTEM_PAUSED = "system.paused"
    SYSTEM_KILL_SWITCH = "system.kill_switch"
    METRIC_UPDATE = "metric.update"


@dataclass(frozen=True)
class Event:
    event_id: str
    run_id: str
    ts: datetime
    type: EventType
    severity: EventSeverity
    symbol: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required")
        if not self.run_id.strip():
            raise ValueError("run_id is required")
        object.__setattr__(self, "type", EventType(self.type))
        object.__setattr__(self, "severity", EventSeverity(self.severity))
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if self.ts.tzinfo is None:
            object.__setattr__(self, "ts", self.ts.replace(tzinfo=UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "run_id": self.run_id,
            "ts": self.ts.isoformat(),
            "type": self.type.value,
            "severity": self.severity.value,
            "symbol": self.symbol,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        timestamp = data["ts"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            event_id=str(data["event_id"]),
            run_id=str(data["run_id"]),
            ts=timestamp,
            type=EventType(data["type"]),
            severity=EventSeverity(data["severity"]),
            symbol=data.get("symbol"),
            payload=dict(data.get("payload", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> Event:
        return cls.from_dict(json.loads(raw))