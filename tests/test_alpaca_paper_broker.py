from types import SimpleNamespace

import alpaca.trading.client as alpaca_client_module

from stock_trade.brokers.alpaca_paper import AlpacaPaperBroker, _client_order_id
from stock_trade.config import Settings
from stock_trade.execution.planner import TradePlan, TradePlanItem


def _plan() -> TradePlan:
    return TradePlan(
        generated_at="2026-06-02T00:00:00+00:00",
        account_equity=100_000,
        mode="paper",
        items=[
            TradePlanItem(
                symbol="SPY",
                strategy="trend",
                target_weight=0.25,
                target_notional=25_000,
                score=1.0,
                validation_sharpe=1.0,
                test_sharpe=1.0,
                test_max_drawdown=-0.05,
                params="{}",
            ),
            TradePlanItem(
                symbol="QQQ",
                strategy="trend",
                target_weight=0.25,
                target_notional=25_000,
                score=1.0,
                validation_sharpe=1.0,
                test_sharpe=1.0,
                test_max_drawdown=-0.05,
                params="{}",
            ),
        ],
    )


def test_alpaca_paper_broker_always_constructs_paper_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeTradingClient:
        def __init__(self, api_key: str, secret: str, paper: bool) -> None:
            captured["api_key"] = api_key
            captured["secret"] = secret
            captured["paper"] = paper

    monkeypatch.setattr(alpaca_client_module, "TradingClient", FakeTradingClient)

    AlpacaPaperBroker(
        Settings(
            trading_mode="paper",
            allow_paper_orders=True,
            alpaca_api_key="paper-key",
            alpaca_api_secret="paper-secret",
        )
    )

    assert captured == {"api_key": "paper-key", "secret": "paper-secret", "paper": True}


def test_submit_buy_plan_submits_only_positive_delta_notional() -> None:
    submitted_orders = []

    class FakeClient:
        def get_all_positions(self):
            return [
                SimpleNamespace(symbol="SPY", market_value="24000"),
                SimpleNamespace(symbol="QQQ", market_value="26000"),
            ]

        def submit_order(self, order_data):
            submitted_orders.append(order_data)
            return SimpleNamespace(id="order-1")

    broker = object.__new__(AlpacaPaperBroker)
    broker.client = FakeClient()

    submitted = broker.submit_buy_plan(_plan())

    assert len(submitted) == 1
    assert submitted[0].symbol == "SPY"
    assert submitted[0].notional == 1_000
    assert submitted_orders[0].notional == 1_000


def test_client_order_id_is_stable_for_same_plan() -> None:
    plan = _plan()

    assert _client_order_id(plan, "SPY") == _client_order_id(plan, "SPY")
    assert _client_order_id(plan, "SPY") != _client_order_id(plan, "QQQ")


def test_client_order_id_is_stable_for_equivalent_plan_intent() -> None:
    first = _plan()
    second = TradePlan(
        generated_at="2026-06-03T00:00:00+00:00",
        account_equity=first.account_equity,
        mode=first.mode,
        items=first.items,
    )

    assert _client_order_id(first, "SPY") == _client_order_id(second, "SPY")


def test_broker_path_does_not_expose_raw_secret(monkeypatch) -> None:
    raw_secret = "raw-paper-secret"

    class FakeTradingClient:
        def __init__(self, api_key: str, secret: str, paper: bool) -> None:
            self.api_key = api_key
            self.secret = secret
            self.paper = paper

    monkeypatch.setattr(alpaca_client_module, "TradingClient", FakeTradingClient)

    broker = AlpacaPaperBroker(
        Settings(
            trading_mode="paper",
            allow_paper_orders=True,
            alpaca_api_key="paper-key",
            alpaca_api_secret=raw_secret,
        )
    )

    assert raw_secret not in repr(broker)
    assert raw_secret not in str(broker)
    assert raw_secret not in repr(_plan())


def test_cancel_open_orders_returns_cancelled_count() -> None:
    class FakeClient:
        def cancel_orders(self):
            return [SimpleNamespace(id="order-1"), SimpleNamespace(id="order-2")]

    broker = object.__new__(AlpacaPaperBroker)
    broker.client = FakeClient()

    assert broker.cancel_open_orders() == 2