# Research Notes

Goal: build a high-value automated paper-trading loop that can research strategies, rank them, and submit orders only to a demo account after explicit approval.

## Source Findings

- Alpaca paper trading is globally available with email signup, uses separate paper keys, and simulates the live Trading API at `https://paper-api.alpaca.markets`. It does not model market impact, information leakage, full slippage, queue position, dividends, or regulatory fees.
- `alpaca-py` is the official Python SDK. It exposes `TradingClient`, typed order request objects, historical data clients, streaming clients, and paper/sandbox credentials.
- VectorBT is best for fast research sweeps. It can run thousands of parameter combinations across assets/time periods with pandas, NumPy, Numba, and optional Rust kernels. It is not an execution engine.
- Backtesting.py is strong for simple single-strategy research and interactive plots, but it does not provide broker execution.
- NautilusTrader is the serious long-term engine if we need research-to-live parity, event-driven execution, multi-venue support, and deterministic simulation. It is more complex than needed for a first paper bot.
- Freqtrade is mature for crypto bots, dry-run mode, hyperopt, and exchange support, but it is crypto-first and GPL-licensed.
- QuantConnect LEAN is a mature open-source engine for backtesting and live trading, but it is heavier and C#-centric even though strategies can be Python.
- Microsoft Qlib is strong for ML alpha research, factor mining, model training, and portfolio backtests, but it is not the fastest route to broker-paper execution.
- Lumibot is directly aligned with agentic trading and Alpaca paper trading: same Python strategy class for backtests and broker execution, with AI-agent patterns. It is promising for phase 2, but this repo starts with deterministic gates first.

## Decision

Use a lean Python scaffold now:

- yfinance for daily research data.
- deterministic strategy sweeps for first-pass candidates.
- train / validation / holdout-test split to reduce overfitting.
- validation metrics select candidates; test metrics are final reporting only.
- explicit fees and slippage.
- Alpaca paper execution behind `TRADING_MODE=paper`, `ALLOW_PAPER_ORDERS=true`, and `--yes`.

Upgrade paths:

- Add VectorBT for larger sweeps once the baseline is verified.
- Add Lumibot if we want same-code backtest plus paper execution with AI trading committees.
- Add NautilusTrader if we need professional event-driven simulation and multi-venue execution parity.

## Strategy Candidates In MVP

- Trend following: SMA fast/slow filters.
- Breakout: Donchian-style highs with trailing-mean exits.
- Mean reversion: RSI entries gated by a 200-day trend filter.

These are deliberately boring. The edge comes from validation discipline, position sizing, and iteration speed, not from trusting a complicated model on day one.