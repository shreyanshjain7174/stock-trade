import pandas as pd

from stock_trade.agents.protocols import CandidateDecision, RiskDecision
from stock_trade.agents.pseudo_committee import PseudoCommittee


def test_pseudo_committee_reviews_every_candidate() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "trend",
                "score": 1.2,
                "latest_signal": True,
                "validation_sharpe": 1.0,
                "validation_max_drawdown": -0.05,
            },
            {
                "symbol": "QQQ",
                "strategy": "trend",
                "score": -0.2,
                "latest_signal": True,
                "validation_sharpe": -0.1,
                "validation_max_drawdown": -0.05,
            },
        ]
    )

    reviews = PseudoCommittee().review(leaderboard)

    assert [review.symbol for review in reviews] == ["SPY", "QQQ"]
    assert all(isinstance(review, CandidateDecision) for review in reviews)
    assert reviews[0].risk_decision is RiskDecision.APPROVED
    assert reviews[1].risk_decision is RiskDecision.REJECTED


def test_pseudo_committee_blocks_inactive_signals() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "trend",
                "score": 1.2,
                "latest_signal": False,
                "validation_sharpe": 1.0,
                "validation_max_drawdown": -0.05,
            }
        ]
    )

    review = PseudoCommittee().review(leaderboard)[0]

    assert review.risk_decision is RiskDecision.BLOCKED
    assert review.risk_reason == "inactive_signal"
    assert "broker" not in " ".join(review.tool_names)


def test_pseudo_committee_resize_decision_carries_multiplier_and_portfolio_note() -> None:
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "strategy": "trend",
                "score": 1.2,
                "latest_signal": True,
                "validation_sharpe": 1.0,
                "validation_max_drawdown": -0.30,
            }
        ]
    )

    review = PseudoCommittee().review(leaderboard)[0]

    assert review.risk_decision is RiskDecision.RESIZED
    assert review.size_multiplier == 0.5
    assert review.portfolio_decision == "resize"