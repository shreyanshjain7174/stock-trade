# stock-trade

Algorithmic trading research and Alpaca paper-trading scaffold. The objective is to move quickly toward a system that can find candidate strategies, validate them, and execute only on a demo account behind explicit safety gates.

This is not financial advice and it does not guarantee profit. It is demo-first infrastructure for disciplined experimentation.

## What It Does

- Downloads adjusted daily prices with `yfinance`.
- Tests trend-following, breakout, and trend-filtered mean-reversion candidates.
- Uses train / validation / test splits to reduce overfitting.
- Includes fees and slippage in backtests.
- Builds a gated long-only paper trade plan.
- Can submit Alpaca paper orders only after explicit env and CLI approval.

## Quick Start

```bash
uv sync --dev
cp .env.example .env
uv run stock-trade research
```

Review the generated files:

- `artifacts/research/leaderboard.csv`
- `artifacts/research/trade_plan.json`

Run the local offline RALPH smoke test:

```bash
uv run python scripts/run_local_ralph_smoke.py --json
```

That command uses synthetic price data, writes a local SQLite audit trail, calls the FastAPI read/control contracts, and confirms paper execution remains blocked without enabled gates and credentials.

Preview the paper plan:

```bash
uv run stock-trade paper-plan
```

Preview only plan items that passed the walk-forward consistency filter:

```bash
uv run stock-trade paper-plan --require-consistency
```

Check strategy consistency across rolling train / validation / test windows:

```bash
uv run stock-trade research-walk-forward --symbols SPY,QQQ,IWM,GLD,TLT --start 2020-01-01
```

This writes `artifacts/research/walk_forward_windows.csv` and `artifacts/research/walk_forward_summary.csv`. Treat it as a robustness filter before trusting any small-window swing result.

Run a bounded paper-only research loop that refreshes the leaderboard, walk-forward consistency report, raw plan, and consistency-filtered plan:

```bash
uv run stock-trade research-loop --iterations 3 --start 2018-01-01
```

This writes `artifacts/research/research_loop_summary.csv` and `artifacts/research/consistent_trade_plan.json`. The consistency plan is selected from all current signals that passed walk-forward robustness checks, not just from the raw top-ranked plan. It does not submit orders; use it as the continuous learning loop before any separately gated paper execution.

Submit to Alpaca paper only after adding paper credentials to `.env`:

```bash
TRADING_MODE=paper ALLOW_PAPER_ORDERS=true uv run stock-trade paper-execute --yes
```

`paper-execute --yes` requires `artifacts/research/walk_forward_summary.csv` by default and filters the plan to strategies marked `consistent=true`. Use `--skip-consistency-gate` only for explicit research exceptions.
When `artifacts/research/consistent_trade_plan.json` exists, `paper-execute --yes` uses that consistency-selected plan by default instead of re-filtering only the raw top-ranked plan.

## Safety Defaults

- No live trading adapter exists.
- Default mode is research-only.
- `paper-execute` is dry-run unless `--yes` is passed.
- Even with `--yes`, execution fails unless `TRADING_MODE=paper` and `ALLOW_PAPER_ORDERS=true` are set.

## Dashboard

The operator dashboard lives under `dashboard/` and talks to the FastAPI API.

```bash
npm --prefix dashboard run dev
```

The first viewport always shows paper/research mode, broker/data status, execution gate status, and the kill switch. The five screens are Command, Timeline, Research, Risk, and Settings.

## Alpaca MCP

VS Code MCP configuration lives in `.vscode/mcp.json`. It launches the official `alpaca-mcp-server` through `scripts/run_alpaca_mcp.py`, which reads local paper credentials from `.env` and maps this app's `ALPACA_API_SECRET` to the server's expected `ALPACA_SECRET_KEY`.

The MCP server is restricted by default to read-oriented market-data toolsets:

```text
assets,stock-data,news,corporate-actions
```

This avoids exposing MCP order-placement tools while the project remains in demo-first research mode.

For a one-shot read-only paper account and market-clock check through MCP, run:

```bash
uv run python scripts/show_alpaca_account_clock_mcp.py --json
```

That helper temporarily enables only the `account,assets` MCP toolsets, calls `get_account_info` and `get_clock`, prints sanitized fields, and exits. It does not expose or call order tools.

## Research Direction

See `docs/research.md` for the source scan and framework decision. The short version: start lean with deterministic gates plus Alpaca paper trading, then consider VectorBT for bigger sweeps, Lumibot for agentic backtesting, and NautilusTrader for production-grade event-driven parity.
