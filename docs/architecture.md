# Architecture

## Flow

1. Download adjusted daily closes for a small ETF/stock universe.
2. Generate long-only candidate positions from deterministic strategies.
3. Backtest each candidate with next-bar exposure, fees, and slippage.
4. Split history into train, validation, and test segments.
5. Rank strategies by validation Sharpe with validation drawdown penalty.
6. Build a paper trade plan only from candidates that pass risk gates.
7. Report holdout-test metrics without using them for selection.
8. Resize the paper plan to current demo-account equity before order submission.
9. Submit only positive delta Alpaca paper buys when all execution gates are enabled.

## Modules

- `stock_trade.research.data`: market data ingestion.
- `stock_trade.research.strategies`: candidate strategy definitions.
- `stock_trade.research.backtest`: long-only backtest engine and metrics.
- `stock_trade.research.sweep`: cross-symbol strategy sweep.
- `stock_trade.risk`: reusable risk limits and gate checks.
- `stock_trade.execution.planner`: converts research results into a target paper plan.
- `stock_trade.brokers.alpaca_paper`: Alpaca paper broker adapter.
- `stock_trade.cli`: command-line interface.

## Safety Gates

- Default mode is research only.
- Paper orders require `TRADING_MODE=paper`.
- Paper orders require `ALLOW_PAPER_ORDERS=true`.
- Paper orders require `stock-trade paper-execute --yes`.
- No live trading adapter exists in this scaffold.