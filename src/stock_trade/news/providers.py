from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from stock_trade.news.models import NewsEvent


class MissingNewsProviderCredentialError(RuntimeError):
    pass


class JsonFetcher(Protocol):
    def __call__(self, url: str, params: dict[str, str]) -> object: ...


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


def default_json_fetcher(url: str, params: dict[str, str]) -> object:
    query = urlencode(params)
    request = Request(f"{url}?{query}", headers={"User-Agent": "stock-trade-news/0.1"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_requested_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        value = symbol.strip().upper()
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)


def as_mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}