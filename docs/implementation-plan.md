# Implementation Plan

## Goal

Build a paper-trading research loop that can discover candidate strategies, generate a gated trade plan, and submit demo orders through Alpaca paper trading.

## Tasks

- [x] Scaffold Python package with uv.
- [x] Research public frameworks and demo execution options.
- [x] Add deterministic strategy sweep and backtest engine.
- [x] Add risk gates and paper trade planner.
- [x] Add Alpaca paper broker adapter behind explicit safety flags.
- [x] Add tests for lookahead protection and risk gates.
- [x] Run dependency sync, lint, and tests.
- [x] Run one research sweep and inspect generated plan.

## Done When

- [x] `uv run pytest` passes.
- [x] `uv run ruff check .` passes.
- [x] `uv run stock-trade research` generates `artifacts/research/leaderboard.csv` and `trade_plan.json`.
- [x] `stock-trade paper-execute` remains dry-run unless paper-order gates are explicitly enabled.