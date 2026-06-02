import pytest

from stock_trade.loop.state import LoopMode, LoopState


def test_loop_state_can_pause_and_resume_from_paper_mode() -> None:
    state = LoopState(mode=LoopMode.PAPER)

    paused = state.pause("operator")
    resumed = paused.resume("operator")

    assert paused.mode is LoopMode.PAUSED
    assert paused.reason == "operator"
    assert resumed.mode is LoopMode.PAPER
    assert resumed.reason is None


def test_loop_state_blocks_execution_when_not_paper() -> None:
    assert LoopState(mode=LoopMode.RESEARCH).can_execute is False
    assert LoopState(mode=LoopMode.PAPER).can_execute is True
    assert LoopState(mode=LoopMode.PAUSED).can_execute is False
    assert LoopState(mode=LoopMode.BLOCKED).can_execute is False
    assert LoopState(mode=LoopMode.KILLED).can_execute is False


def test_killed_state_cannot_resume_without_manual_reset() -> None:
    killed = LoopState(mode=LoopMode.PAPER).kill("operator")

    with pytest.raises(RuntimeError, match="manual reset"):
        killed.resume("operator")
    assert killed.manual_reset().mode is LoopMode.RESEARCH


def test_blocked_state_can_resume_to_research_only() -> None:
    blocked = LoopState(mode=LoopMode.PAPER).block("risk breach")

    resumed = blocked.resume("operator")

    assert blocked.mode is LoopMode.BLOCKED
    assert resumed.mode is LoopMode.RESEARCH