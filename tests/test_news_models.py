from datetime import UTC, datetime, timedelta

import pytest

from stock_trade.news.models import NewsEvent, NewsEventType
from stock_trade.news.providers import FixtureNewsProvider, NewsProvider


def _event(symbols: list[str] | None = None) -> NewsEvent:
    provider_ts = datetime(2026, 6, 2, 13, 30, tzinfo=UTC)
    received_ts = provider_ts + timedelta(seconds=12)
    return NewsEvent(
        provider="fixture",
        provider_event_id="headline-1",
        provider_timestamp=provider_ts,
        received_timestamp=received_ts,
        symbols=["spy", "SPY", "qqq"] if symbols is None else symbols,
        title="Fed minutes move indexes",
        url="https://example.test/news/headline-1",
        summary="A fixture headline for offline replay.",
        sentiment=0.25,
        event_type=NewsEventType.MACRO,
        raw={"source": "unit-test"},
    )


def test_news_event_round_trips_json_for_replay() -> None:
    event = _event()

    restored = NewsEvent.from_json(event.to_json())

    assert restored == event
    assert restored.to_dict()["provider_timestamp"] == "2026-06-02T13:30:00+00:00"
    assert restored.to_dict()["received_timestamp"] == "2026-06-02T13:30:12+00:00"
    assert restored.symbols == ("SPY", "QQQ")


def test_news_event_validates_required_fields_and_sentiment_bounds() -> None:
    with pytest.raises(ValueError, match="provider is required"):
        _event().__class__(**{**_event().to_dict(), "provider": " "})

    with pytest.raises(ValueError, match="at least one symbol"):
        _event([])

    with pytest.raises(ValueError, match="sentiment"):
        _event().__class__(**{**_event().to_dict(), "sentiment": 2.0})


def test_news_event_raw_metadata_is_immutable() -> None:
    raw = {"source": "fixture"}
    event = NewsEvent(
        provider="fixture",
        provider_event_id="headline-2",
        provider_timestamp=datetime(2026, 6, 2, tzinfo=UTC),
        received_timestamp=datetime(2026, 6, 2, 0, 0, 5, tzinfo=UTC),
        symbols=["GLD"],
        title="Gold moves",
        url=None,
        summary=None,
        sentiment=None,
        event_type=NewsEventType.HEADLINE,
        raw=raw,
    )

    raw["source"] = "changed"

    with pytest.raises(TypeError):
        event.raw["source"] = "mutated"
    assert event.to_dict()["raw"] == {"source": "fixture"}


def test_fixture_provider_filters_by_symbol_without_network_calls() -> None:
    provider: NewsProvider = FixtureNewsProvider([_event(["SPY"]), _event(["GLD"])])

    events = provider.fetch_latest(["spy"])

    assert len(events) == 1
    assert events[0].symbols == ("SPY",)
    assert events[0].received_timestamp > events[0].provider_timestamp