from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from stock_trade.news.models import NewsEvent, NewsEventType
from stock_trade.news.providers import (
    JsonFetcher,
    MissingNewsProviderCredentialError,
    as_mapping,
    default_json_fetcher,
    normalize_requested_symbols,
)


class PolygonNewsProvider:
    def __init__(
        self,
        api_key: str | None,
        *,
        fetch_json: JsonFetcher = default_json_fetcher,
        now: Callable[[], datetime] | None = None,
        base_url: str = "https://api.polygon.io/v2/reference/news",
        limit: int = 50,
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.fetch_json = fetch_json
        self.now = now or (lambda: datetime.now(UTC))
        self.base_url = base_url
        self.limit = limit

    def fetch_latest(self, symbols: Sequence[str]) -> tuple[NewsEvent, ...]:
        if not self.api_key:
            raise MissingNewsProviderCredentialError("POLYGON_API_KEY is required")
        requested = normalize_requested_symbols(symbols)
        if not requested:
            return ()

        received_timestamp = self.now()
        events: list[NewsEvent] = []
        for symbol in requested:
            payload = as_mapping(
                self.fetch_json(
                    self.base_url,
                    {"ticker": symbol, "limit": str(self.limit), "apiKey": self.api_key},
                )
            )
            results = payload.get("results", [])
            if isinstance(results, list):
                events.extend(
                    _map_polygon_event(item, received_timestamp) for item in results if item
                )
        return tuple(events)


def _map_polygon_event(item: dict[str, Any], received_timestamp: datetime) -> NewsEvent:
    return NewsEvent(
        provider="polygon",
        provider_event_id=str(item.get("id") or item.get("article_url") or item["title"]),
        provider_timestamp=_parse_iso_timestamp(str(item["published_utc"])),
        received_timestamp=received_timestamp,
        symbols=list(item.get("tickers", [])),
        title=str(item["title"]),
        url=item.get("article_url"),
        summary=item.get("description"),
        sentiment=_polygon_sentiment(item.get("insights")),
        event_type=NewsEventType.HEADLINE,
        raw=item,
    )


def _parse_iso_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _polygon_sentiment(insights: object) -> float | None:
    if not isinstance(insights, list) or not insights:
        return None
    sentiment = str(insights[0].get("sentiment", "")).lower()
    if sentiment == "positive":
        return 1.0
    if sentiment == "negative":
        return -1.0
    if sentiment == "neutral":
        return 0.0
    return None