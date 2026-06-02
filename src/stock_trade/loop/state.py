from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LoopMode(StrEnum):
    RESEARCH = "research"
    PAPER = "paper"
    PAUSED = "paused"
    BLOCKED = "blocked"
    KILLED = "killed"


@dataclass(frozen=True)
class LoopState:
    mode: LoopMode = LoopMode.RESEARCH
    previous_mode: LoopMode | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", LoopMode(self.mode))
        if self.previous_mode is not None:
            object.__setattr__(self, "previous_mode", LoopMode(self.previous_mode))

    @property
    def can_execute(self) -> bool:
        return self.mode is LoopMode.PAPER

    def pause(self, reason: str) -> LoopState:
        if self.mode is LoopMode.KILLED:
            raise RuntimeError("Killed loop requires manual reset before state changes")
        return LoopState(mode=LoopMode.PAUSED, previous_mode=self.mode, reason=reason)

    def resume(self, reason: str) -> LoopState:
        if self.mode is LoopMode.KILLED:
            raise RuntimeError("Killed loop requires manual reset")
        if self.mode is LoopMode.BLOCKED:
            return LoopState(mode=LoopMode.RESEARCH, reason=None)
        if self.mode is not LoopMode.PAUSED:
            return self
        return LoopState(mode=self.previous_mode or LoopMode.RESEARCH, reason=None)

    def block(self, reason: str) -> LoopState:
        if self.mode is LoopMode.KILLED:
            return self
        return LoopState(mode=LoopMode.BLOCKED, previous_mode=self.mode, reason=reason)

    def kill(self, reason: str) -> LoopState:
        return LoopState(mode=LoopMode.KILLED, previous_mode=self.mode, reason=reason)

    def manual_reset(self) -> LoopState:
        return LoopState(mode=LoopMode.RESEARCH, reason=None)