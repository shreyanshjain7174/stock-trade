# News Swing Strategy And Agent Swarm Implementation Plan

> **For Copilot:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Build a paper-only research pipeline for short-window swing strategies, fast news/event signals, and a governed swarm of agents that can research and propose trades without direct broker authority.

**Architecture:** Keep execution centralized in `stock-trade`; use external agents for research, news summarization, feature extraction, and review. NineVigil/Clawdlinux can run agent swarms as isolated Kubernetes `AgentWorkload`s with budgets, Cilium egress policy, Argo DAG execution, artifacts, and audit trails. Agents submit signed research artifacts into this repo/API; deterministic backtests, risk gates, and paper-only controls decide whether anything reaches Alpaca paper.

**Tech Stack:** Python 3.12, pandas, yfinance/Alpaca market data, provider news APIs, SQLite, FastAPI, React dashboard, NineVigil AgentWorkload CRDs, Argo Workflows, Cilium egress policy, MinIO/artifact storage.

---

## Phase 1: Swing Strategy Baseline

### Task 1.1: Expand Short-Window Strategy Set

**Files:**
- Modify: `src/stock_trade/research/strategies.py`
- Create/Modify: `tests/test_strategies.py`

**Steps:**
1. Add short-window swing pullback candidates.
2. Add 10-20 day breakout candidates with short exits.
3. Add 5-10 day momentum burst candidates.
4. Verify all strategy signals are executed next bar by the existing backtester.

**Acceptance Criteria:**
- Strategies are included in `strategy_specs()`.
- Offline tests prove each strategy emits bounded long-only positions.
- Existing sweep and planner tests still pass.

### Task 1.2: Walk-Forward Consistency Report

**Files:**
- Create: `src/stock_trade/research/walk_forward.py`
- Create: `tests/test_walk_forward.py`
- Modify: `src/stock_trade/cli.py`
- Modify: `README.md`

**Steps:**
1. Split history into rolling train/validation/test windows.
2. Measure consistency across windows: validation Sharpe hit rate, test Sharpe hit rate, drawdown breach count, trade count, exposure, turnover.
3. Add CLI command `stock-trade research-walk-forward`.
4. Emit `artifacts/research/walk_forward.csv`.

**Acceptance Criteria:**
- Strategy selection requires repeated validation success, not one lucky window.
- Report includes costs, slippage, drawdown, and out-of-sample test metrics.

## Phase 2: News Feed Research

### Task 2.1: Provider Abstraction

**Files:**
- Create: `src/stock_trade/news/models.py`
- Create: `src/stock_trade/news/providers.py`
- Create: `tests/test_news_models.py`

**Steps:**
1. Define `NewsEvent` with provider, provider timestamp, received timestamp, symbols, title, URL, summary, sentiment, event type, and raw metadata.
2. Add provider interface with `fetch_latest(symbols)` and optional streaming hook.
3. Add fixture provider for offline tests.

**Acceptance Criteria:**
- News events can be stored and replayed without calling paid APIs.
- Provider timestamps are distinct from local received timestamps.

### Task 2.2: MVP Provider Implementations

**Files:**
- Create: `src/stock_trade/news/finnhub.py`
- Create: `src/stock_trade/news/polygon.py`
- Create: `src/stock_trade/news/gdelt.py`
- Create: `tests/test_news_providers.py`

**Steps:**
1. Implement Finnhub REST/WebSocket adapter behind optional env keys.
2. Implement Polygon ticker news adapter behind optional env keys.
3. Implement GDELT polling adapter for free delayed/event research.
4. Add rate-limit and licensing notes in docs.

**Acceptance Criteria:**
- Missing API keys fail closed with clear errors.
- Tests use fixtures and do not hit the network.

### Task 2.3: News-to-Price Reaction Backtest

**Files:**
- Create: `src/stock_trade/research/news_reaction.py`
- Create: `tests/test_news_reaction.py`

**Steps:**
1. Join historical news events to price bars using only information known at the event received timestamp.
2. Evaluate 1-day, 3-day, 5-day, and 10-day forward returns after event categories.
3. Add null-model comparisons against random event times.
4. Report hit rate, average return, drawdown, turnover, and slippage-adjusted performance.

**Acceptance Criteria:**
- No look-ahead from article revisions or late provider crawl timestamps.
- Signal must beat a randomized baseline before becoming a strategy candidate.

## Phase 3: Agent Swarm Operating Model

### Task 3.1: Agent Roles

**Files:**
- Create: `docs/agent-swarm.md`
- Modify: `docs/architecture.md`

**Agent roles:**
- Market data scout: validates price and corporate action data freshness.
- News scout: fetches headlines/events and measures feed latency.
- Strategy researcher: proposes small-window strategy candidates.
- Backtest verifier: runs walk-forward tests and rejects overfit candidates.
- Risk reviewer: checks drawdown, concentration, exposure, turnover, and liquidity.
- Execution sentinel: confirms paper-only gates and blocks live execution.
- Operator reporter: summarizes what happened for the dashboard.

**Acceptance Criteria:**
- No agent role has direct broker credentials.
- Every agent output is a persisted artifact with run ID and source metadata.

### Task 3.2: NineVigil/Clawdlinux Integration

**Files:**
- Create: `infra/agentworkloads/research-swarm.yaml`
- Create: `infra/agentworkloads/news-scout.yaml`
- Create: `infra/agentworkloads/backtest-verifier.yaml`
- Create: `docs/clawdlinux-integration.md`

**Steps:**
1. Model the swarm as NineVigil `AgentWorkload`s with tenant quotas and per-agent budgets.
2. Restrict egress with Cilium FQDN policy to approved data providers only.
3. Use Argo DAGs for research → analyze → backtest → risk-review → report.
4. Persist agent artifacts to object storage and submit only artifact references to `stock-trade`.
5. Use ACL summaries for Kubernetes/OpenAPI/Postgres context to keep agent prompts small.

**Acceptance Criteria:**
- The swarm can scale research throughput without increasing broker authority.
- Stock-trade remains the single paper execution authority.
- Agent costs and outputs are auditable per workload.

### Task 3.3: Human-In-The-Loop Gates

**Files:**
- Modify: `src/stock_trade/api/app.py`
- Modify: `dashboard/src/App.tsx`
- Create: `tests/test_agent_artifact_intake.py`

**Steps:**
1. Add an artifact intake endpoint for agent proposals.
2. Require deterministic validation before proposals can become trade plans.
3. Show proposal provenance, backtest consistency, and risk reasons in the dashboard.
4. Keep paper execution behind confirmation token and environment gates.

**Acceptance Criteria:**
- Agents can propose; only the controlled backend can plan/execute.
- Operator sees provenance and consistency before approving paper execution.

## Definition Of Done

- Swing strategies are backtested with costs, slippage, drawdown, and out-of-sample validation.
- News providers are abstracted and fixture-tested before paid API integration.
- News signals are benchmarked against randomized baselines.
- NineVigil runs research swarms with budgets, policy, and artifacts.
- No agent can directly place live or paper orders.
- Paper execution remains gated and visible in the dashboard.