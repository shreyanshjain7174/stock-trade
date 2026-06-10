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
- Swing pullbacks: 3-5 day RSI pullbacks inside a 20-day trend, with short moving-average exits.
- Swing breakouts: 10-20 day breakouts with 5-10 day trailing-low exits.
- Swing momentum bursts: 5-10 day momentum gated by a 20-30 day trend filter.

These are deliberately boring. The edge comes from validation discipline, position sizing, and iteration speed, not from trusting a complicated model on day one.

## Fast News And Signal Feed Candidates

The next signal layer should treat news as research input, not guaranteed alpha. Every feed must be backtested with provider timestamps, observed ingestion latency, costs, slippage, and out-of-sample validation.

Recommended MVP order:

1. Finnhub premium news and sentiment: developer-friendly REST/WebSocket coverage, useful for streaming headline and sentiment experiments.
2. Polygon.io ticker news plus market data: strong fit for joining headlines to price reaction in one vendor ecosystem.
3. Tiingo news: useful for historical headline research and affordable ticker-tagged news access.
4. GDELT: free global news/event/sentiment data at roughly 15-minute cadence, useful for research but not wire-speed trading.
5. Benzinga newswire/squawk: higher-cost upgrade path for faster “why it moved” headlines and analyst/events coverage.

Enterprise upgrade path:

- Bloomberg B-PIPE/Enterprise Access, LSEG/Refinitiv, Dow Jones/Factiva/Newswires, RavenPack, and Dataminr are more Bloomberg-terminal-like, but they are enterprise-priced and contract-heavy. Use only after the MVP proves the strategy class has signal value.

Implementation notes:

- Store both provider timestamp and local received timestamp.
- The current `stock_trade.news` package includes a replay-safe `NewsEvent` model, an offline `FixtureNewsProvider`, and fixture-tested Finnhub, Polygon, and GDELT adapters. Finnhub and Polygon fail closed when API keys are missing; GDELT is free but delayed research input.
- `stock_trade.research.news_reaction` evaluates headline/event reactions using only each event's local `received_timestamp`, then compares cost-adjusted forward returns against a deterministic null baseline before anything can graduate into strategy research.
- Separate headline ingestion, entity/ticker linking, sentiment/event extraction, strategy research, and execution gates.
- Never let a news agent place orders. Agents can propose candidates; deterministic risk and paper execution gates decide what can be submitted.
