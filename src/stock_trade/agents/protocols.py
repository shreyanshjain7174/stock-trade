from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

import pandas as pd


class RiskDecision(StrEnum):
    APPROVED = "approved"
    RESIZED = "resized"
    REJECTED = "rejected"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CandidateDecision:
    symbol: str
    strategy: str
    risk_decision: RiskDecision
    risk_reason: str
    bull_case: str
    bear_case: str
    portfolio_decision: str
    params: str = ""
    size_multiplier: float = 1.0
    tool_names: tuple[str, ...] = field(default_factory=tuple)


class CommitteeProtocol(Protocol):
    def review(self, leaderboard: pd.DataFrame) -> list[CandidateDecision]:
        pass