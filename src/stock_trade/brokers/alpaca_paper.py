from dataclasses import dataclass
from hashlib import sha256

from stock_trade.config import Settings
from stock_trade.execution.planner import TradePlan


@dataclass(frozen=True)
class SubmittedOrder:
    symbol: str
    side: str
    notional: float
    broker_order_id: str


class AlpacaPaperBroker:
    def __init__(self, settings: Settings) -> None:
        settings.require_paper_trading()

        from alpaca.trading.client import TradingClient

        secret = settings.alpaca_api_secret.get_secret_value() if settings.alpaca_api_secret else ""
        self.client = TradingClient(settings.alpaca_api_key, secret, paper=True)

    def account_equity(self) -> float:
        account = self.client.get_account()
        return float(account.equity)

    def cancel_open_orders(self) -> int:
        return len(self.client.cancel_orders())

    def submit_buy_plan(self, plan: TradePlan) -> list[SubmittedOrder]:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        current_values = self._current_market_values()
        submitted: list[SubmittedOrder] = []
        for item in plan.items:
            current_notional = current_values.get(item.symbol, 0.0)
            delta_notional = round(item.target_notional - current_notional, 2)
            if delta_notional <= 1.0:
                continue
            order = self.client.submit_order(
                MarketOrderRequest(
                    symbol=item.symbol,
                    notional=delta_notional,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY,
                    client_order_id=_client_order_id(plan, item.symbol),
                )
            )
            submitted.append(
                SubmittedOrder(
                    symbol=item.symbol,
                    side="buy",
                    notional=delta_notional,
                    broker_order_id=str(order.id),
                )
            )
        return submitted

    def _current_market_values(self) -> dict[str, float]:
        positions = self.client.get_all_positions()
        return {str(position.symbol): float(position.market_value) for position in positions}


def _client_order_id(plan: TradePlan, symbol: str) -> str:
    matching_items = [item for item in plan.items if item.symbol == symbol]
    if matching_items:
        item = matching_items[0]
        seed = (
            f"{plan.mode}:{item.symbol}:{item.strategy}:{item.target_weight:.8f}:"
            f"{item.target_notional:.2f}:{item.params}"
        ).encode()
    else:
        seed = f"{plan.mode}:{symbol}".encode()
    digest = sha256(seed).hexdigest()[:20]
    return f"paper-{symbol.lower()}-{digest}"