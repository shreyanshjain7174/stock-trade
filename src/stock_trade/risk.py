from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_positions: int
    max_position_pct: float
    cash_buffer_pct: float
    max_drawdown_pct: float
    min_validation_sharpe: float

    def target_weight(self, selected_count: int) -> float:
        if selected_count <= 0:
            return 0.0
        available_weight = max(0.0, 1.0 - self.cash_buffer_pct)
        equal_weight = available_weight / selected_count
        return min(self.max_position_pct, equal_weight)

    def max_position_notional(self, account_equity: float) -> float:
        return account_equity * self.max_position_pct

    def passes_strategy_gate(
        self,
        validation_sharpe: float,
        validation_max_drawdown: float,
    ) -> bool:
        if validation_sharpe < self.min_validation_sharpe:
            return False
        return validation_max_drawdown >= -abs(self.max_drawdown_pct)

    def cash_buffer_notional(self, account_equity: float) -> float:
        return account_equity * self.cash_buffer_pct

    def max_deployable_notional(self, account_equity: float) -> float:
        return max(0.0, account_equity - self.cash_buffer_notional(account_equity))