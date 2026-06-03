from datetime import UTC, datetime

import pandas as pd

from stock_trade.news.models import NewsEvent, NewsEventType
from stock_trade.research.news_reaction import evaluate_news_reactions


def _event(
    event_id: str,
    received: datetime,
    symbol: str = "SPY",
    event_type: NewsEventType = NewsEventType.MACRO,
) -> NewsEvent:
    return NewsEvent(
        provider="fixture",
        provider_event_id=event_id,
        provider_timestamp=datetime(2024, 1, 1, 9, tzinfo=UTC),
        received_timestamp=received,
        symbols=[symbol],
        title=f"{symbol} fixture",
        event_type=event_type,
    )


def test_news_reaction_uses_received_timestamp_not_provider_timestamp() -> None:
    close = pd.DataFrame(
        {"SPY": [100.0, 101.0, 102.0, 112.2, 120.0]},
        index=pd.date_range("2024-01-01", periods=5, freq="D", tz=UTC),
    )
    event = _event("late-crawl", datetime(2024, 1, 2, 12, tzinfo=UTC))

    report = evaluate_news_reactions([event], close, horizons=(1,), fee_bps=0, slippage_bps=0)
    sample = report.samples.iloc[0]

    assert sample["entry_timestamp"] == "2024-01-03T00:00:00+00:00"
    assert sample["exit_timestamp"] == "2024-01-04T00:00:00+00:00"
    assert sample["forward_return"] == 0.10


def test_news_reaction_summary_has_deterministic_null_baseline() -> None:
    close = pd.DataFrame(
        {"SPY": [100, 101, 102, 103, 104, 105, 106, 107], "QQQ": [50, 49, 51, 52, 53, 52, 54, 55]},
        index=pd.date_range("2024-01-01", periods=8, freq="D", tz=UTC),
        dtype=float,
    )
    events = [
        _event("spy-1", datetime(2024, 1, 2, 12, tzinfo=UTC), "SPY", NewsEventType.MACRO),
        _event("spy-2", datetime(2024, 1, 4, 12, tzinfo=UTC), "SPY", NewsEventType.MACRO),
        _event("qqq-1", datetime(2024, 1, 3, 12, tzinfo=UTC), "QQQ", NewsEventType.EARNINGS),
    ]

    first = evaluate_news_reactions(events, close, horizons=(1, 3), random_seed=11)
    second = evaluate_news_reactions(events, close, horizons=(1, 3), random_seed=11)

    pd.testing.assert_frame_equal(first.summary, second.summary)
    assert set(first.summary["horizon"]) == {1, 3}
    assert set(first.summary.columns).issuperset(
        {
            "symbol",
            "event_type",
            "horizon",
            "event_count",
            "hit_rate",
            "avg_net_return",
            "baseline_avg_net_return",
            "beats_baseline",
            "max_drawdown",
            "turnover",
        }
    )