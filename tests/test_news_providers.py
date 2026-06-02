from datetime import UTC, datetime

import pytest

from stock_trade.news.finnhub import FinnhubNewsProvider
from stock_trade.news.gdelt import GdeltNewsProvider
from stock_trade.news.polygon import PolygonNewsProvider
from stock_trade.news.providers import MissingNewsProviderCredentialError


def test_finnhub_provider_fails_closed_without_api_key() -> None:
    provider = FinnhubNewsProvider(api_key=None)

    with pytest.raises(MissingNewsProviderCredentialError):
        provider.fetch_latest(["SPY"])


def test_finnhub_provider_maps_company_news_payload() -> None:
    calls = []

    def fetch_json(url: str, params: dict[str, str]) -> object:
        calls.append((url, params))
        return [
            {
                "id": 101,
                "datetime": 1_780_406_400,
                "headline": "SPY headline",
                "summary": "Fixture summary",
                "url": "https://example.test/finnhub/101",
                "related": "SPY,QQQ",
                "category": "company",
            }
        ]

    provider = FinnhubNewsProvider(
        api_key="test-key",
        fetch_json=fetch_json,
        now=lambda: datetime(2026, 6, 2, 14, tzinfo=UTC),
    )

    events = provider.fetch_latest(["spy"])

    assert calls[0][1]["symbol"] == "SPY"
    assert calls[0][1]["token"] == "test-key"
    assert events[0].provider == "finnhub"
    assert events[0].provider_event_id == "101"
    assert events[0].provider_timestamp == datetime(2026, 6, 2, 13, 20, tzinfo=UTC)
    assert events[0].received_timestamp == datetime(2026, 6, 2, 14, tzinfo=UTC)
    assert events[0].symbols == ("SPY", "QQQ")


def test_polygon_provider_fails_closed_without_api_key() -> None:
    provider = PolygonNewsProvider(api_key="")

    with pytest.raises(MissingNewsProviderCredentialError):
        provider.fetch_latest(["SPY"])


def test_polygon_provider_maps_ticker_news_payload() -> None:
    def fetch_json(url: str, params: dict[str, str]) -> object:
        assert url.endswith("/v2/reference/news")
        assert params["ticker"] == "GLD"
        assert params["apiKey"] == "polygon-key"
        return {
            "results": [
                {
                    "id": "poly-1",
                    "published_utc": "2026-06-02T13:31:00Z",
                    "tickers": ["GLD", "SPY"],
                    "title": "Gold headline",
                    "article_url": "https://example.test/polygon/poly-1",
                    "description": "Polygon fixture.",
                    "insights": [{"ticker": "GLD", "sentiment": "positive"}],
                }
            ]
        }

    provider = PolygonNewsProvider(
        api_key="polygon-key",
        fetch_json=fetch_json,
        now=lambda: datetime(2026, 6, 2, 14, tzinfo=UTC),
    )

    events = provider.fetch_latest(["gld"])

    assert events[0].provider == "polygon"
    assert events[0].provider_event_id == "poly-1"
    assert events[0].sentiment == 1.0
    assert events[0].symbols == ("GLD", "SPY")


def test_gdelt_provider_maps_delayed_article_payload_without_key() -> None:
    def fetch_json(url: str, params: dict[str, str]) -> object:
        assert url.endswith("/api/v2/doc/doc")
        assert "SPY" in params["query"]
        assert params["format"] == "json"
        return {
            "articles": [
                {
                    "url": "https://example.test/gdelt/story",
                    "title": "Global macro story",
                    "seendate": "20260602T133000Z",
                    "sourceCountry": "US",
                    "domain": "example.test",
                }
            ]
        }

    provider = GdeltNewsProvider(
        fetch_json=fetch_json,
        now=lambda: datetime(2026, 6, 2, 14, tzinfo=UTC),
    )

    events = provider.fetch_latest(["spy"])

    assert events[0].provider == "gdelt"
    assert events[0].provider_timestamp == datetime(2026, 6, 2, 13, 30, tzinfo=UTC)
    assert events[0].received_timestamp == datetime(2026, 6, 2, 14, tzinfo=UTC)
    assert events[0].symbols == ("SPY",)