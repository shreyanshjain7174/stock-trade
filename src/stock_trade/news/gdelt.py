from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from stock_trade.news.models import NewsEvent, NewsEventType
from stock_trade.news.providers import (
    JsonFetcher,
    as_mapping,
    default_json_fetcher,
    normalize_requested_symbols,
)


class GdeltNewsProvider:
    def __init__(
        self,
        *,
        fetch_json: JsonFetcher = default_json_fetcher,
        now: Callable[[], datetime] | None = None,
        base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc",
        max_records: int = 50,
    ) -> None:
        self.fetch_json = fetch_json
        self.now = now or (lambda: datetime.now(UTC))
        self.base_url = base_url
        self.max_records = max_records

    def fetch_latest(self, symbols: Sequence[str]) -> tuple[NewsEvent, ...]:
        requested = normalize_requested_symbols(symbols)
        if not requested:
            return ()

        received_timestamp = self.now()
        query = " OR ".join(requested)
        payload = as_mapping(
            self.fetch_json(
                self.base_url,
                {
                    "query": query,
                    "mode": "ArtList",
                    "format": "json",
                    "maxrecords": str(self.max_records),
                    "sort": "DateDesc",
                },
            )
        )
        articles = payload.get("articles", [])
        if not isinstance(articles, list):
            return ()
        return tuple(
            _map_gdelt_article(article, requested, received_timestamp)
            for article in articles
            if article
        )


def _map_gdelt_article(
    article: dict[str, Any],
    requested_symbols: Sequence[str],
    received_timestamp: datetime,
) -> NewsEvent:
    return NewsEvent(
        provider="gdelt",
        provider_event_id=str(article.get("url") or article["title"]),
        provider_timestamp=_parse_gdelt_seen_date(str(article["seendate"])),
        received_timestamp=received_timestamp,
        symbols=requested_symbols,
        title=str(article["title"]),
        url=article.get("url"),
        summary=None,
        sentiment=None,
        event_type=NewsEventType.HEADLINE,
        raw=article,
    )


def _parse_gdelt_seen_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)