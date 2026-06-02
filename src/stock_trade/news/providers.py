from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from stock_trade.news.models import NewsEvent


class NewsProvider(Protocol):
    def fetch_latest(self, symbols: Sequence[str]) -> tuple[NewsEvent, ...]: ...


class FixtureNewsProvider:
    def __init__(self, events: Sequence[NewsEvent]) -> None:
        self._events = tuple(events)

    def fetch_latest(self, symbols: Sequence[str]) -> tuple[NewsEvent, ...]:
        requested = {symbol.strip().upper() for symbol in symbols if symbol.strip()}
        if not requested:
            return self._events
        return tuple(event for event in self._events if requested.intersection(event.symbols))