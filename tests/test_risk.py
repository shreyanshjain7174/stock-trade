from stock_trade.risk import RiskLimits


def test_target_weight_respects_position_cap() -> None:
    limits = RiskLimits(
        max_positions=5,
        max_position_pct=0.20,
        cash_buffer_pct=0.10,
        max_drawdown_pct=0.25,
        min_validation_sharpe=0.3,
    )

    assert limits.target_weight(3) == 0.20


def test_validation_gate_blocks_deep_drawdown() -> None:
    limits = RiskLimits(
        max_positions=3,
        max_position_pct=0.25,
        cash_buffer_pct=0.10,
        max_drawdown_pct=0.20,
        min_validation_sharpe=0.3,
    )

    assert not limits.passes_strategy_gate(1.0, -0.35)
    assert limits.passes_strategy_gate(1.0, -0.10)