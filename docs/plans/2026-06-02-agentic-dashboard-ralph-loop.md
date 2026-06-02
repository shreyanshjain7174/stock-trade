# Agentic Dashboard RALPH Loop Implementation Plan

> **For Copilot:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan task-by-task.

**Goal:** Build an end-to-end paper-only agentic trading loop with a live operator dashboard, event audit trail, risk gates, and Stitch-assisted UI workflow.

**Architecture:** The system uses a RALPH loop: Research, Analyze, Limit, Plan, Hand-off/Harden. The loop calls existing deterministic research and paper-planning modules, adds an event/persistence spine, then exposes state through a FastAPI dashboard API and a React operator console. Execution remains Alpaca paper-only unless a separate live-mode risk review is completed later.

**Tech Stack:** Python 3.12, uv, pytest, Ruff, FastAPI, SQLite, DuckDB, Alpaca paper API, React/TypeScript, Tailwind/CSS variables, WebSocket or SSE, Stitch-generated UI references.

---

## RALPH Operating Loop

Each implementation cycle follows this control loop:

1. **Research**: deterministic strategy sweep or agentic backtest creates candidates and artifacts.
2. **Analyze**: agent committee annotates candidates with bull, bear, market regime, and evidence notes.
3. **Limit**: risk gates approve, resize, reject, or block every candidate.
4. **Plan**: planner converts approved candidates into a paper trade plan with position caps, cash buffer, and idempotency keys.
5. **Hand-off / Harden**: broker hand-off executes only in paper mode, emits audit events, then verification agents harden tests and docs.

Every RALPH cycle must emit typed events, persist an audit trail, and end with verification before the next task begins.

## Subagent Loop

Use Claude Opus 4.8 for all reasoning-heavy implementation and reviews.

For each task:

1. **Planner Subagent, Opus 4.8**: confirms task scope and acceptance criteria.
2. **Coder Subagent, Opus 4.8**: implements the smallest TDD slice.
3. **Spec Reviewer Subagent, Opus 4.8**: checks the code against this plan only.
4. **Code Reviewer Subagent, Opus 4.8**: checks maintainability, safety, and hidden regressions.
5. **Verifier Subagent, Opus 4.8**: runs targeted tests, then broader checks.
6. **Agent Manager**: integrates results, updates this plan, and moves to the next task.

Do not dispatch multiple coder subagents against the same files. Parallelize only independent review, research, and UI tasks.

## Phase 0: Guardrail Baseline

### Task 0.1: Lock Current Paper-Only Behavior

**Status:** Done. Implemented guardrail tests in `tests/test_config.py` and `tests/test_planner.py`.

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_backtest.py`
- Modify: `tests/test_risk.py`

**Subagents:**
- Coder: `python-testing-patterns`, Opus 4.8
- Reviewer: `risk-control-reviewer`, Opus 4.8

**Steps:**
1. Add tests proving `paper-execute` remains dry-run without explicit confirmation.
2. Add tests proving `Settings.require_paper_trading()` blocks research mode, missing `ALLOW_PAPER_ORDERS`, and missing credentials.
3. Add a test proving no raw `ALPACA_API_SECRET` appears in serialized settings, plans, or errors.
4. Run `uv run pytest tests/test_config.py tests/test_planner.py -q`.
5. Run `uv run ruff check .`.

**Acceptance Criteria:**
- Paper execution cannot happen without `TRADING_MODE=paper`, `ALLOW_PAPER_ORDERS=true`, credentials, and explicit confirmation.
- No test output or artifact contains a raw secret.

### Task 0.2: Offline Price Fixture For CI

**Status:** Done. Implemented deterministic in-test price fixture in `tests/test_research_smoke.py` instead of a large static CSV file.

**Files:**
- Create: `tests/fixtures/prices_spy_qqq.csv`
- Create: `tests/test_research_smoke.py`
- Modify: `src/stock_trade/research/data.py` only if needed for fixture injection.

**Subagents:**
- Coder: `python-testing-patterns`, Opus 4.8
- Verifier: `ci-verification-runner`, Opus 4.8

**Steps:**
1. Create a tiny deterministic OHLC/close fixture covering enough bars for sweep tests.
2. Add a test that runs the sweep without network access.
3. Assert `leaderboard` and `TradePlan` are produced from fixture data.
4. Run `uv run pytest tests/test_research_smoke.py -q`.

**Acceptance Criteria:**
- CI can test research without yfinance or network access.
- Fixture smoke test exercises selection, risk gate, and plan generation.

## Phase 1: Event Spine

### Task 1.1: Event Envelope

**Status:** Done. Implemented `src/stock_trade/events/models.py` with immutable payload handling and JSON round-trip tests.

**Files:**
- Create: `src/stock_trade/events/__init__.py`
- Create: `src/stock_trade/events/models.py`
- Create: `tests/test_events.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `backend-security-coder`, Opus 4.8

**Steps:**
1. Define an `EventSeverity` enum: `info`, `warning`, `critical`.
2. Define an `EventType` enum for `research.started`, `research.completed`, `agent.tool_call`, `risk.gate`, `plan.created`, `broker.order`, `broker.fill`, `system.paused`, `system.kill_switch`, `metric.update`.
3. Define an immutable event model with `event_id`, `run_id`, `ts`, `type`, `severity`, `symbol`, `payload`.
4. Add JSON serialization and deserialization.
5. Test schema validation and round-trip behavior.

**Acceptance Criteria:**
- Event JSON matches the envelope in `docs/agentic-live-dashboard-research.md`.
- Invalid severity/type is rejected.

### Task 1.2: Event Bus And JSONL Sink

**Status:** Done. Implemented `src/stock_trade/events/bus.py` with subscriber error isolation and JSONL append tests.

**Files:**
- Create: `src/stock_trade/events/bus.py`
- Create: `tests/test_event_bus.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `code-reviewer`, Opus 4.8

**Steps:**
1. Add an in-process `EventBus` with `publish()` and `subscribe()`.
2. Add a `JsonlEventSink` writing to `artifacts/events/{run_id}.jsonl`.
3. Add tests for append-only ordering and subscriber notification.
4. Run `uv run pytest tests/test_events.py tests/test_event_bus.py -q`.

**Acceptance Criteria:**
- Every event can be persisted as one JSON line.
- Subscribers receive events in publish order.

## Phase 2: Persistence Layer

### Task 2.1: SQLite Store

**Status:** Done. Implemented `src/stock_trade/store/sqlite.py` with WAL mode, idempotent writes, insertion-order events, run status updates, and append-only traces.

**Files:**
- Create: `src/stock_trade/store/__init__.py`
- Create: `src/stock_trade/store/sqlite.py`
- Create: `tests/test_store.py`

**Subagents:**
- Coder: `database-architect`, Opus 4.8
- Reviewer: `database-optimizer`, Opus 4.8

**Steps:**
1. Add SQLite tables for `runs`, `events`, `plans`, and `agent_traces`.
2. Enable WAL mode for API/loop concurrency.
3. Add repository methods: `create_run`, `append_event`, `save_plan`, `list_runs`, `get_run`, `get_trace`.
4. Test idempotent writes and event retrieval by `run_id`.

**Acceptance Criteria:**
- Store can persist and retrieve a complete RALPH run.
- SQLite is safe for a local single-writer/multiple-reader MVP.

## Phase 3: Deterministic RALPH Orchestrator

### Task 3.1: Loop State

**Status:** Done. Implemented `src/stock_trade/loop/state.py` with pause, resume, block, kill, and manual reset behavior.

**Files:**
- Create: `src/stock_trade/loop/__init__.py`
- Create: `src/stock_trade/loop/state.py`
- Create: `tests/test_loop_state.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `risk-control-reviewer`, Opus 4.8

**Steps:**
1. Add states: `research`, `paper`, `paused`, `blocked`, `killed`.
2. Add transition rules: pause, resume, block, kill.
3. Test that `killed` cannot resume without manual reset.

**Acceptance Criteria:**
- Execution refuses in `paused`, `blocked`, and `killed` states.

### Task 3.2: RALPH Cycle Without Agents

**Status:** Done. Implemented deterministic `src/stock_trade/loop/ralph.py` with research, risk, plan persistence, and event emission. Broker hand-off remains out of scope until Phase 5.

**Files:**
- Create: `src/stock_trade/loop/ralph.py`
- Create: `tests/test_ralph_loop.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `spec-reviewer`, Opus 4.8

**Steps:**
1. Implement `run_cycle(settings, bus, store, prices)`.
2. Call current research sweep, validation-only risk gates, and planner.
3. Emit events for Research, Limit, and Plan stages.
4. Do not submit broker orders in this task.
5. Test successful cycle and empty-candidate cycle.

**Acceptance Criteria:**
- RALPH cycle creates a persisted run and trade plan.
- Empty or blocked cases submit zero orders and emit a risk event.

## Phase 4: Agent Committee

### Task 4.1: Agent Protocol And Pseudo Committee

**Status:** Done. Implemented deterministic agent protocols and `PseudoCommittee` with approved, resized, rejected, and blocked decisions.

**Files:**
- Create: `src/stock_trade/agents/__init__.py`
- Create: `src/stock_trade/agents/protocols.py`
- Create: `src/stock_trade/agents/pseudo_committee.py`
- Create: `tests/test_agents.py`

**Subagents:**
- Planner: `ai-agents-architect`, Opus 4.8
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `risk-control-reviewer`, Opus 4.8

**Steps:**
1. Define structured outputs for `bull_case`, `bear_case`, `risk_decision`, and `portfolio_decision`.
2. Implement deterministic `PseudoCommittee` that annotates candidates without LLM calls.
3. Add decisions: `approved`, `resized`, `rejected`, `blocked`.
4. Test every candidate receives a risk decision.

**Acceptance Criteria:**
- The agent layer is testable without model keys.
- No agent has direct broker access in this task.

### Task 4.2: Wire Analyze And Limit Stages

**Status:** Done. Wired committee review into `run_cycle`, persisted committee trace data, emitted agent events, and filtered planning by params-stable approved/resized decisions.

**Files:**
- Modify: `src/stock_trade/loop/ralph.py`
- Modify: `tests/test_ralph_loop.py`

**Subagents:**
- Coder: `ai-agent-development`, Opus 4.8
- Reviewer: `backend-security-coder`, Opus 4.8

**Steps:**
1. Insert `Analyze` stage after Research.
2. Insert agent risk decision into `Limit` stage.
3. Ensure rejected/blocked candidates never reach the planner.
4. Emit agent and risk events.

**Acceptance Criteria:**
- Every planned order is traceable to an agent risk decision.

## Phase 5: Paper Hand-Off And Kill Switch

### Task 5.1: Broker Safety Tests

**Status:** Done. Added mocked Alpaca paper broker tests for paper-only construction, delta-only buys, and stable client order IDs.

**Files:**
- Create: `tests/test_alpaca_paper_broker.py`
- Modify: `src/stock_trade/brokers/alpaca_paper.py` only if test exposes a gap.

**Subagents:**
- Coder: `broker-safety-auditor`, Opus 4.8
- Reviewer: `backend-security-coder`, Opus 4.8

**Steps:**
1. Mock Alpaca client.
2. Assert `TradingClient(..., paper=True)` is always used.
3. Assert current positions reduce buy notional by delta.
4. Assert stable `client_order_id` for identical plan.
5. Assert no raw secrets are logged or serialized.

**Acceptance Criteria:**
- Broker adapter is paper-only and idempotency behavior is covered.

### Task 5.2: Hand-Off Stage

**Status:** Done. Added optional paper execution hand-off to `run_cycle`, kill-switch support, mocked tests, and stable intent-based Alpaca client order IDs for repeated equivalent plans.

**Files:**
- Modify: `src/stock_trade/loop/ralph.py`
- Modify: `src/stock_trade/loop/state.py`
- Create: `tests/test_ralph_handoff.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `risk-control-reviewer`, Opus 4.8

**Steps:**
1. Add optional `execute=False` flag to `run_cycle`.
2. If `execute=True`, call broker only after settings gates pass and loop state allows execution.
3. Emit `broker.order` events for submitted paper orders.
4. Add kill-switch behavior that cancels open paper orders and pauses loop state.

**Acceptance Criteria:**
- Default cycle creates a plan but submits no orders.
- Execute path is paper-only and mocked in tests.
- Kill switch cancels open orders and blocks new orders.

## Phase 6: Scheduler

### Task 6.1: Local Scheduler

**Status:** Done. Implemented interval scheduler with injectable clock, pause/block/kill skips, no broker execution in research mode, and unique persisted scheduler events.

**Files:**
- Create: `src/stock_trade/loop/scheduler.py`
- Create: `tests/test_scheduler.py`

**Subagents:**
- Coder: `workflow-orchestration-patterns`, Opus 4.8
- Reviewer: `devops-troubleshooter`, Opus 4.8

**Steps:**
1. Add a simple interval/daily scheduler with injectable clock.
2. Honor pause/resume/kill state.
3. Emit scheduler events.
4. Test skipped cycles while paused and no execution in research mode.

**Acceptance Criteria:**
- Scheduler never bypasses RALPH safety gates.

## Phase 7: Dashboard API

### Task 7.1: FastAPI Read Endpoints

**Status:** Done. Implemented read-only FastAPI endpoints, local dashboard CORS, uniform mode/execution flags, missing-run 404s, and secret-redaction tests.

**Files:**
- Create: `src/stock_trade/api/__init__.py`
- Create: `src/stock_trade/api/app.py`
- Create: `src/stock_trade/api/schemas.py`
- Create: `tests/test_api_read.py`
- Modify: `pyproject.toml` to add FastAPI and Uvicorn.

**Subagents:**
- Coder: `fastapi-pro`, Opus 4.8
- Reviewer: `backend-security-coder`, Opus 4.8

**Steps:**
1. Implement `/health`.
2. Implement read endpoints for account snapshot, positions, orders, fills, risk status, runs, leaderboard, and traces.
3. Ensure mode badge data is returned by every dashboard bootstrapping endpoint.
4. Test no response contains raw secrets.

**Acceptance Criteria:**
- Dashboard can load all read-only state from API.

### Task 7.2: Event Stream

**Status:** Done. Implemented `/api/events/stream` as an SSE endpoint over persisted event history.

**Files:**
- Modify: `src/stock_trade/api/app.py`
- Create: `tests/test_api_events.py`

**Subagents:**
- Coder: `backend-architect`, Opus 4.8
- Reviewer: `performance-engineer`, Opus 4.8

**Steps:**
1. Add `/api/events/stream` using SSE first.
2. Stream persisted events from the JSONL sink or SQLite store.
3. Test event serialization and reconnect behavior.

**Acceptance Criteria:**
- UI can subscribe to normalized events without polling.

### Task 7.3: Gated Control Endpoints

**Status:** Done. Implemented pause, resume, kill-switch, and gated paper execute endpoints with audit events and backend paper-only enforcement.

**Files:**
- Modify: `src/stock_trade/api/app.py`
- Create: `tests/test_api_controls.py`

**Subagents:**
- Coder: `backend-security-coder`, Opus 4.8
- Reviewer: `security-auditor`, Opus 4.8

**Steps:**
1. Add `POST /api/system/pause`, `resume`, `kill-switch`.
2. Add `POST /api/research/run`, `paper/plan`, `paper/execute`.
3. Require `paper_only=true` and a confirmation token for paper execution.
4. Audit log every action.

**Acceptance Criteria:**
- UI controls cannot bypass backend safety gates.

## Phase 8: Dashboard UI

### Task 8.1: Frontend Scaffold

**Status:** Done. Scaffolded Vite React TypeScript dashboard, added API client, design tokens, and the initial operator command-center shell with persistent mode and kill-switch UI.

**Files:**
- Create: `dashboard/` Vite React TypeScript project.
- Create: `dashboard/src/styles/tokens.css`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/api/client.ts`

**Subagents:**
- Planner: `ui-ux-designer`, Opus 4.8
- Coder: `ui-engineer`, Opus 4.8
- Reviewer: `frontend-security-coder`, Opus 4.8

**Steps:**
1. Scaffold Vite React TypeScript app.
2. Add design tokens from `docs/agentic-live-dashboard-research.md`.
3. Add API client and event stream client.
4. Build shell with persistent mode badge and kill switch.

**Acceptance Criteria:**
- Dashboard starts locally and shows safety status from backend or mock data.

### Task 8.2: Stitch Design Intake

**Status:** Done. Added Stitch prompt pack, design review checklist, and export directory placeholder under `design/stitch/`.

**Files:**
- Create: `design/stitch/prompts.md`
- Create: `design/stitch/review-checklist.md`
- Create: `design/stitch/exports/.gitkeep`

**Subagents:**
- Designer: `stitch-ui-design`, Opus 4.8
- Reviewer: `ui-visual-validator`, Opus 4.8

**Steps:**
1. Copy Command Center, Agent Timeline, and Research Lab prompts from `docs/agentic-live-dashboard-research.md`.
2. Add Risk Cockpit and Settings prompts.
3. Add design review checklist for contrast, focus states, no card-in-card, no secrets, and operator-console density.

**Acceptance Criteria:**
- Stitch workflow is ready for manual export or future MCP automation.

### Task 8.3: Dashboard Screens

**Status:** Done. Split the dashboard into shared primitives, five screen modules, and Vitest/axe coverage for safety-shell behavior.

**Files:**
- Create: `dashboard/src/screens/CommandCenter.tsx`
- Create: `dashboard/src/screens/AgentTimeline.tsx`
- Create: `dashboard/src/screens/ResearchLab.tsx`
- Create: `dashboard/src/screens/RiskCockpit.tsx`
- Create: `dashboard/src/screens/SettingsIntegrations.tsx`
- Create: `dashboard/src/components/ModeBadge.tsx`
- Create: `dashboard/src/components/StatusDot.tsx`
- Create: `dashboard/src/components/RiskChip.tsx`
- Create: `dashboard/src/components/KillSwitchButton.tsx`
- Create: `dashboard/src/components/MetricCard.tsx`
- Create: `dashboard/src/components/DataTable.tsx`
- Create: `dashboard/src/components/TraceDrawer.tsx`
- Create: `dashboard/src/App.test.tsx`

**Subagents:**
- Coder: one `ui-engineer` Opus 4.8 subagent per screen after shared components exist.
- Reviewer: `accessibility-compliance-accessibility-audit`, Opus 4.8

**Steps:**
1. Implement shared components first: `ModeBadge`, `StatusDot`, `RiskChip`, `KillSwitchButton`, `MetricCard`, `DataTable`, `TraceDrawer`.
2. Implement each screen against real or mocked API contracts.
3. Add loading, empty, stale, error, and blocked states.
4. Run frontend tests and accessibility checks.

**Acceptance Criteria:**
- All five screens render critical paper-trading state and never hide mode/safety status.

## Phase 9: End-To-End Verification

### Task 9.1: Full RALPH Smoke Test

**Status:** Done. Added an offline smoke script and pytest coverage that run synthetic prices through RALPH, persist events/plans/traces, call API contracts, and verify paper execution remains blocked.

**Files:**
- Create: `tests/test_end_to_end_ralph.py`
- Create: `scripts/run_local_ralph_smoke.py`

**Subagents:**
- Verifier: `Verifier`, Opus 4.8
- Reviewer: `senior-code-reviewer`, Opus 4.8

**Steps:**
1. Run offline research fixture.
2. Run RALPH cycle with pseudo committee.
3. Persist events and plan.
4. Load API read endpoints.
5. Confirm `paper-execute` remains dry without confirmation.

**Acceptance Criteria:**
- One command proves local loop, audit trail, API, and dashboard contracts work without network or broker secrets.

### Task 9.2: Final Quality Gate

**Status:** Done. README and dashboard research docs were updated, the plan reflects completed work, and final backend/frontend/CLI verification was run.

**Files:**
- Modify: `README.md`
- Modify: `docs/agentic-live-dashboard-research.md`
- Modify: this plan as completed.

**Subagents:**
- Reviewer: `senior-code-reviewer`, Opus 4.8
- Verifier: `Verifier`, Opus 4.8

**Commands:**
```bash
uv run ruff check .
uv run pytest -q
uv run stock-trade research --symbols SPY,QQQ --start 2019-01-01 --end 2024-01-01
uv run stock-trade paper-plan
uv run stock-trade paper-execute
```

Frontend commands after dashboard exists:
```bash
cd dashboard
npm run lint
npm run test
npm run build
```

**Acceptance Criteria:**
- Backend tests pass.
- Frontend lint, tests, and build pass.
- VS Code diagnostics show no errors.
- Final report lists exact commands and results.

## Parallelization Rules

Safe to parallelize:

- UI screen builders after shared components exist.
- Read-only reviews.
- Stitch prompt authoring and backend event-schema work.

Do not parallelize:

- Multiple coders editing `risk.py`, `planner.py`, or `loop/ralph.py`.
- API control endpoint work and broker hand-off safety work.
- Frontend safety-gate work and backend safety-gate changes unless contracts are frozen.

## Definition Of Done

- Local RALPH cycle runs end-to-end in paper/demo mode.
- Dashboard API exposes state, traces, risk, plan, and event stream.
- React dashboard shows command center, agent timeline, research lab, risk cockpit, and settings.
- Stitch prompts and review checklist are saved in `design/stitch/`.
- Kill switch and paper-mode status are visible and backend-enforced.
- Every order has a risk decision, idempotency key, and audit trail.
- No raw secrets appear in logs, artifacts, API responses, or UI.
- All tests, lint, build, and diagnostics pass.