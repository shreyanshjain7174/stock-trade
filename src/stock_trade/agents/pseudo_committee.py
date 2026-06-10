import pandas as pd

from stock_trade.agents.protocols import CandidateDecision, RiskDecision


class PseudoCommittee:
    """Deterministic committee used before LLM-backed agents are introduced."""

    def review(self, leaderboard: pd.DataFrame) -> list[CandidateDecision]:
        return [self._review_row(row) for row in leaderboard.itertuples(index=False)]

    def _review_row(self, row: object) -> CandidateDecision:
        symbol = str(row.symbol)
        strategy = str(row.strategy)
        latest_signal = bool(row.latest_signal)
        score = float(row.score)
        validation_drawdown = float(row.validation_max_drawdown)

        if not latest_signal:
            decision = RiskDecision.BLOCKED
            reason = "inactive_signal"
            portfolio_decision = "exclude"
            size_multiplier = 0.0
        elif score < 0:
            decision = RiskDecision.REJECTED
            reason = "negative_validation_score"
            portfolio_decision = "exclude"
            size_multiplier = 0.0
        elif validation_drawdown < -0.25:
            decision = RiskDecision.RESIZED
            reason = "deep_validation_drawdown"
            portfolio_decision = "resize"
            size_multiplier = 0.5
        else:
            decision = RiskDecision.APPROVED
            reason = "validation_passed"
            portfolio_decision = "include"
            size_multiplier = 1.0

        return CandidateDecision(
            symbol=symbol,
            strategy=strategy,
            risk_decision=decision,
            risk_reason=reason,
            bull_case=f"{symbol} {strategy} has validation evidence worth considering.",
            bear_case=f"{symbol} {strategy} can still fail if the regime changes.",
            portfolio_decision=portfolio_decision,
            params=str(getattr(row, "params", "")),
            size_multiplier=size_multiplier,
            tool_names=("leaderboard", "risk_rules"),
        )