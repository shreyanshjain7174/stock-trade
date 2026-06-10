from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from stock_trade.news.models import NewsEvent, NewsEventType
from stock_trade.news.providers import (
    JsonFetcher,
    MissingNewsProviderCredentialError,
    default_json_fetcher,
    normalize_requested_symbols,
)


class FinnhubNewsProvider:
    def __init__(
        self,
        api_key: str | None,
        *,
        fetch_json: JsonFetcher = default_json_fetcher,
        now: Callable[[], datetime] | None = None,
        base_url: str = "https://finnhub.io/api/v1/company-news",
    ) -> None:
        self.api_key = api_key.strip() if api_key else None
        self.fetch_json = fetch_json
        self.now = now or (lambda: datetime.now(UTC))
        self.base_url = base_url

    def fetch_latest(self, symbols: Sequence[str]) -> tuple[NewsEvent, ...]:
        if not self.api_key:
            raise MissingNewsProviderCredentialError("FINNHUB_API_KEY is required")
        requested = normalize_requested_symbols(symbols)
        if not requested:
            return ()

        received_timestamp = self.now()
        from_date = (received_timestamp - timedelta(days=3)).date().isoformat()
        to_date = received_timestamp.date().isoformat()
        events: list[NewsEvent] = []
        for symbol in requested:
            payload = self.fetch_json(
                self.base_url,
                {"symbol": symbol, "from": from_date, "to": to_date, "token": self.api_key},
            )
            if not isinstance(payload, list):
                continue
            events.extend(
                _map_finnhub_event(item, symbol, received_timestamp) for item in payload if item
            )
        return tuple(events)


def _map_finnhub_event(
    item: dict[str, Any],
    requested_symbol: str,
    received_timestamp: datetime,
) -> NewsEvent:
    related = [symbol.strip() for symbol in str(item.get("related", "")).split(",")]
    symbols = related or [requested_symbol]
    timestamp = datetime.fromtimestamp(int(item["datetime"]), tz=UTC)
    return NewsEvent(
        provider="finnhub",
        provider_event_id=str(item.get("id") or item.get("url") or item["headline"]),
        provider_timestamp=timestamp,
        received_timestamp=received_timestamp,
        symbols=symbols,
        title=str(item["headline"]),
        url=item.get("url"),
        summary=item.get("summary"),
        sentiment=None,
        event_type=NewsEventType.HEADLINE,
        raw=item,
    )