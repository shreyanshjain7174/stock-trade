from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class NewsEventType(StrEnum):
    HEADLINE = "headline"
    EARNINGS = "earnings"
    MACRO = "macro"
    CORPORATE_ACTION = "corporate_action"
    ANALYST_RATING = "analyst_rating"
    OTHER = "other"


@dataclass(frozen=True)
class NewsEvent:
    provider: str
    provider_event_id: str
    provider_timestamp: datetime
    received_timestamp: datetime
    symbols: Sequence[str]
    title: str
    url: str | None = None
    summary: str | None = None
    sentiment: float | None = None
    event_type: NewsEventType = NewsEventType.HEADLINE
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = self.provider.strip()
        provider_event_id = self.provider_event_id.strip()
        title = self.title.strip()
        if not provider:
            raise ValueError("provider is required")
        if not provider_event_id:
            raise ValueError("provider_event_id is required")
        if not title:
            raise ValueError("title is required")
        if self.sentiment is not None and not -1.0 <= float(self.sentiment) <= 1.0:
            raise ValueError("sentiment must be between -1.0 and 1.0")

        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "provider_event_id", provider_event_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "event_type", NewsEventType(self.event_type))
        object.__setattr__(self, "symbols", _normalize_symbols(self.symbols))
        object.__setattr__(self, "provider_timestamp", _coerce_timestamp(self.provider_timestamp))
        object.__setattr__(self, "received_timestamp", _coerce_timestamp(self.received_timestamp))
        object.__setattr__(self, "raw", MappingProxyType(dict(self.raw)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "provider_event_id": self.provider_event_id,
            "provider_timestamp": self.provider_timestamp.isoformat(),
            "received_timestamp": self.received_timestamp.isoformat(),
            "symbols": list(self.symbols),
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "event_type": self.event_type.value,
            "raw": dict(self.raw),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> NewsEvent:
        return cls(
            provider=str(data["provider"]),
            provider_event_id=str(data["provider_event_id"]),
            provider_timestamp=data["provider_timestamp"],
            received_timestamp=data["received_timestamp"],
            symbols=list(data["symbols"]),
            title=str(data["title"]),
            url=data.get("url"),
            summary=data.get("summary"),
            sentiment=data.get("sentiment"),
            event_type=NewsEventType(data.get("event_type", NewsEventType.HEADLINE)),
            raw=dict(data.get("raw", {})),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> NewsEvent:
        return cls.from_dict(json.loads(raw))


def _normalize_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        value = str(symbol).strip().upper()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    if not normalized:
        raise ValueError("at least one symbol is required")
    return tuple(normalized)


def _coerce_timestamp(value: datetime | str) -> datetime:
    timestamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)
    return timestamp