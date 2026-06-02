# Agentic Trading + Live Dashboard Research

## Goal

Design the next phase of this demo-first trading project: an agentic trading loop with a live operator dashboard, strong risk controls, inspectable agent decisions, and a Stitch-assisted UI design workflow.

This remains paper/demo trading until a separate live-mode risk review creates an explicit live gate.

## Key Research Findings

- Google Stitch is an AI UI design tool that generates UI designs and corresponding frontend code from natural language or image prompts. Google describes export paths to HTML/CSS and Figma.
- I did not find a dedicated Stitch MCP tool exposed in this VS Code session. The current practical workflow is either manual Stitch export or a custom MCP wrapper if a usable Stitch API/server is available later.
- Alpaca paper trading gives a real-time simulation environment and separate paper keys. It is useful for demo execution, but does not model market impact, information leakage, full slippage, queue position, dividends, or regulatory fees.
- `alpaca-py` provides typed clients for trading, positions, orders, account state, market data, news, and streaming.
- Lumibot is the fastest route to agentic backtesting: agents run inside the trading loop, can use built-in trading tools, external REST tools, MCP servers by URL, DuckDB time-series queries, replay cache, and JSON/Parquet traces.
- NautilusTrader is a stronger long-term engine if we need deterministic event-driven research/live parity, multi-venue adapters, order books, and nanosecond-level market simulation. It is heavier than needed for the immediate dashboard MVP.

## Recommended Architecture

## Implementation Status

- RALPH loop, event persistence, API read/control endpoints, and paper-only broker gates are implemented for the local MVP.
- The Vite React dashboard now has Command, Timeline, Research, Risk, and Settings screens with a persistent mode/execution/kill-switch status bar.
- Local verification is covered by `scripts/run_local_ralph_smoke.py`, backend pytest, dashboard Vitest, ESLint, and Vite build.
- Stitch remains a manual workflow in this environment because no dedicated Stitch MCP server is exposed.

### Core Services

1. `research-service`
   - Runs deterministic strategy sweeps and agentic backtests.
   - Produces leaderboard, trade plan, tearsheet metrics, traces, and artifacts.
   - Starts with current `stock_trade` modules; later can add Lumibot for agent-in-loop backtests.

2. `agent-service`
   - Orchestrates specialist agents:
     - `market_researcher`: market structure, trend, regime, macro context.
     - `bull_case`: strongest risk-on thesis.
     - `bear_case`: drawdown, catalyst, liquidity, and data-quality objections.
     - `risk_manager`: position caps, cash buffer, drawdown gates, kill-switch review.
     - `portfolio_manager`: converts approved thesis into a paper trade plan.
   - Uses read-only tools by default. Only a final portfolio/execution agent can request orders.
   - Stores every prompt, tool call, output summary, warnings, and decision artifact.

3. `broker-service`
   - Alpaca paper adapter first.
   - Responsibilities: account state, positions, open orders, fills, cancel/replace, delta-only rebalancing.
   - No live adapter in MVP.

4. `dashboard-api`
   - FastAPI is the simplest fit with the current Python repo.
   - Exposes REST for historical artifacts and WebSocket/SSE for live updates.
   - Serves the dashboard separately from the trading loop to keep execution isolated.

5. `dashboard-ui`
   - Next.js or Vite React + TypeScript.
   - Tailwind or CSS variables for a dashboard-specific design system.
   - Charting: lightweight charts for price/equity, Recharts/Nivo/ECharts for operational metrics, TanStack Table for audit logs.

### Storage

- SQLite for the first local MVP.
- DuckDB for time-series research artifacts and agent query tables.
- Postgres later if multi-user, hosted deployment, or long-running jobs matter.
- File artifacts remain useful: CSV leaderboard, JSON trade plan, JSONL event logs, Parquet traces.

### Real-Time Event Stream

Use a normalized event envelope:

```json
{
  "event_id": "uuid",
  "run_id": "agent-run-or-session-id",
  "ts": "2026-06-02T00:00:00Z",
  "type": "agent.tool_call | risk.gate | broker.fill | broker.order | metric.update",
  "severity": "info | warning | critical",
  "symbol": "SPY",
  "payload": {}
}
```

Dashboard transport:

- WebSocket for live broker/agent events.
- Server-sent events if we want a simpler one-way stream.
- Polling fallback for artifacts and historical runs.

## Dashboard Screens

### 1. Command Center

Purpose: see whether the system is safe, active, and making money in paper mode.

Required UI:

- Mode badge: `research`, `paper`, `blocked`, `paused`.
- Equity curve and daily P&L.
- Exposure by asset and sector.
- Current positions, open orders, latest fills.
- Risk panel: cash buffer, max drawdown, concentration, open-order count, stale-data status.
- Kill switch: prominent, confirmation-gated, always visible.

### 2. Agent Decision Timeline

Purpose: inspect why the agent wanted a trade.

Required UI:

- Chronological run timeline.
- Tool calls and results.
- Research/bull/bear/risk/portfolio handoffs.
- Warnings: missing data, future-date clamp, low confidence, rejected order.
- Decision card: proposed trade, approved/rejected, risk reason.

### 3. Research Lab

Purpose: compare deterministic and agentic strategy candidates before paper execution.

Required UI:

- Leaderboard table with validation score and holdout test metrics.
- Parameter set drawer.
- Backtest equity/drawdown/trades tabs.
- Artifact download links.
- Promote-to-paper-plan button behind review state.

### 4. Risk Cockpit

Purpose: keep the system honest.

Required UI:

- Risk limit editor.
- Drawdown ladder and exposure heatmap.
- Correlation matrix.
- Rejected trade log.
- Manual pause/resume controls.

### 5. Settings + Integrations

Purpose: configure paper broker and model providers without exposing secrets.

Required UI:

- Broker connection status, not raw keys.
- Model provider status, token/cost budget, replay cache status.
- MCP server registry: name, URL, enabled state, timeout, last health check.
- Audit export.

## UI/UX Direction

Design stance: `institutional dark operations desk`.

Use a quiet, dense, low-glare trading interface. This should feel like an operator console, not a marketing SaaS page.

Design system guidance from the UI/UX skill:

- Pattern: real-time monitoring.
- Style: dark mode / OLED.
- Palette:
  - background `#0F172A`
  - text `#F8FAFC`
  - primary amber `#F59E0B`
  - secondary amber `#FBBF24`
  - action accent violet `#8B5CF6`
- Typography: Fira Code for numeric/technical labels, Fira Sans for body text.
- Effects: minimal glow only for critical status, visible focus rings, no decorative gradients.
- Accessibility: 4.5:1 contrast minimum, 44px touch targets, keyboard navigation, reduced-motion support.

## Stitch Workflow

### Current Practical Path

1. Use Stitch web UI with the prompts below.
2. Generate desktop-first dashboard screens.
3. Export to Figma or HTML/CSS.
4. Translate exported design into React components.
5. Build against real dashboard API contracts rather than static mock data.

### If A Stitch MCP Server Becomes Available

Needed MCP capabilities:

- `stitch.create_project(name, platform, theme)`
- `stitch.generate_screen(project_id, prompt, references)`
- `stitch.generate_flow(project_id, screens[])`
- `stitch.annotate(project_id, screen_id, selector_or_region, instruction)`
- `stitch.export(project_id, target="figma|html_css")`
- `stitch.get_assets(project_id)`

Needed integration config:

- MCP server URL.
- Auth method/API key, stored outside repo.
- Export directory mapping, e.g. `design/stitch/exports/`.
- A design review checklist before code import.

### Stitch Prompt: Command Center

```text
Desktop web dashboard for an agentic paper-trading operations desk.

Key features:
- Dense top status bar with mode badge, market session status, broker connection, data freshness, model provider health, and kill switch.
- Main grid with paper account equity curve, daily P&L, drawdown, current exposure, and open risk alerts.
- Positions table with symbol, quantity, market value, target weight, drift, unrealized P&L, and last agent decision.
- Right-side agent activity stream showing researcher, bull, bear, risk manager, and portfolio manager handoffs.
- Bottom panel for open orders and latest fills.

Visual style:
- Institutional dark operations desk, low-glare OLED background.
- Amber risk accents, violet action accents, crisp chart lines, high-contrast text.
- Use Fira Code for numbers and technical labels, Fira Sans for body copy.
- Compact but readable, no marketing hero, no decorative cards inside cards.

Platform: responsive desktop-first web dashboard, 1440px primary, tablet fallback.
```

### Stitch Prompt: Agent Timeline

```text
Agent decision trace screen for a paper-trading AI system.

Key features:
- Left run selector with run ID, timestamp, model, cache status, and final decision.
- Central vertical timeline of agent steps: market researcher, bull case, bear case, risk manager, portfolio manager.
- Expandable tool-call rows with tool name, arguments, latency, warning count, and result preview.
- Decision summary panel with proposed orders, rejected orders, risk reasons, and confidence.
- Warning strip for look-ahead risks, stale data, missing tool results, and order blocks.

Visual style:
- Dark forensic audit console, precise typography, strong hierarchy.
- Use amber for warnings, red only for blocked/critical states, green only for verified safe states.
- Make auditability the visual anchor: timelines, badges, compact tables, and trace drawers.

Platform: desktop web.
```

### Stitch Prompt: Research Lab

```text
Quant research lab dashboard for comparing strategy candidates before paper trading.

Key features:
- Strategy leaderboard with validation score, validation Sharpe, validation drawdown, holdout test Sharpe, holdout test drawdown, latest signal, and promote-to-plan action.
- Equity curve and drawdown chart for selected strategy.
- Tabs for trades, parameters, artifacts, and agent notes.
- Filter controls for symbol, strategy family, risk gate pass/fail, and date range.
- Clear label that holdout test metrics are report-only and not used for selection.

Visual style:
- Technical trading research terminal, dark mode, compact analytic layout.
- Fira Code numeric cells, accessible heatmap coloring, no oversized hero sections.

Platform: responsive web dashboard.
```

## API Surface Needed

Minimum backend endpoints:

- `GET /health`
- `GET /api/account/snapshot`
- `GET /api/positions`
- `GET /api/orders/open`
- `GET /api/fills/recent`
- `GET /api/risk/status`
- `GET /api/research/runs`
- `GET /api/research/runs/{run_id}`
- `GET /api/research/runs/{run_id}/leaderboard`
- `GET /api/agent/runs`
- `GET /api/agent/runs/{run_id}/trace`
- `POST /api/research/run`
- `POST /api/paper/plan`
- `POST /api/paper/execute` with `paper_only=true` and confirmation token.
- `POST /api/system/pause`
- `POST /api/system/resume`
- `POST /api/system/kill-switch`
- `GET /api/events/stream` via SSE or WebSocket.

## Safety Requirements

- Dashboard must display current mode at all times.
- Paper execution is disabled unless backend mode is `paper`.
- Live execution cannot exist until a separate live-mode review adds it.
- All order submissions require idempotency keys.
- Every agent-suggested order must include a risk decision: approved, resized, rejected, or blocked.
- Kill switch cancels open orders and pauses the scheduler.
- The dashboard must never render secrets.

## Build Phases

### Phase 1: Local Operator Dashboard

- Add FastAPI app wrapping existing research and paper-plan commands.
- Persist events to SQLite and artifacts to `artifacts/`.
- Build React dashboard with static and polling data.
- Add Stitch-generated design reference screens.

### Phase 2: Real-Time Paper Trading Loop

- Add scheduler for daily/interval paper plan generation.
- Add Alpaca stream ingestion for fills/orders/account updates.
- Add WebSocket/SSE event stream.
- Add pause/resume/kill-switch.

### Phase 3: Agentic Research

- Add Lumibot or a custom agent orchestration layer.
- Add agent traces, replay cache, model/token/cost telemetry.
- Add external tools for Alpaca news, FRED macro, SEC filings, and market regime.
- Keep order tools disabled except for final portfolio manager role.

### Phase 4: Advanced Research Engine

- Add VectorBT for large parameter sweeps.
- Consider NautilusTrader if we need event-driven parity and higher-fidelity execution simulation.
- Add walk-forward testing and Monte Carlo stress tests.

## Definition Of Done For MVP

- Dashboard shows account snapshot, positions, open orders, latest fills, current trade plan, and risk status.
- Research run can be launched from UI and updates leaderboard artifacts.
- Paper plan can be reviewed from UI but execution remains gated.
- Agent trace screen can display at least deterministic pseudo-agent decisions or imported Lumibot traces.
- All dashboard actions are audit logged.
- Tests cover API safety gates, paper-only mode, event schema, and frontend critical rendering states.