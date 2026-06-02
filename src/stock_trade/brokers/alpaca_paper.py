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
        return self.submit_plan(plan)

    def submit_plan(self, plan: TradePlan) -> list[SubmittedOrder]:
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        current_values = self._current_market_values()
        target_values = {item.symbol: item.target_notional for item in plan.items}
        plan_symbols = [item.symbol for item in plan.items]
        symbols = plan_symbols + sorted(set(current_values) - set(target_values))
        submitted: list[SubmittedOrder] = []
        for symbol in symbols:
            current_notional = current_values.get(symbol, 0.0)
            target_notional = target_values.get(symbol, 0.0)
            delta_notional = round(target_notional - current_notional, 2)
            if abs(delta_notional) <= 1.0:
                continue
            side = "buy" if delta_notional > 0 else "sell"
            notional = abs(delta_notional)
            order = self.client.submit_order(
                MarketOrderRequest(
                    symbol=symbol,
                    notional=notional,
                    side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                    time_in_force=TimeInForce.DAY,
                    client_order_id=_client_order_id(plan, symbol),
                )
            )
            submitted.append(
                SubmittedOrder(
                    symbol=symbol,
                    side=side,
                    notional=notional,
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