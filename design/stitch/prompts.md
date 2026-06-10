# Stitch Prompt Pack: Agentic Trading Desk

Use these prompts in Google Stitch to generate dashboard design references. Export selected screens to `design/stitch/exports/` as HTML/CSS or Figma, then translate into React components using the dashboard design tokens.

## Shared Direction

Design stance: institutional dark operations desk.

Constraints:

- No landing page or marketing hero.
- No card-in-card layouts.
- Keep data dense but readable.
- Show paper/research mode and safety state on every screen.
- Use Fira Code for numeric/technical labels and Fira Sans for body copy.
- Palette: `#0F172A` background, `#F8FAFC` text, `#F59E0B` primary amber, `#FBBF24` secondary amber, `#8B5CF6` action accent.

## Command Center

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

## Agent Timeline

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

## Research Lab

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

## Risk Cockpit

```text
Risk cockpit screen for an agentic paper-trading dashboard.

Key features:
- Risk limit editor for max positions, max position percent, cash buffer, max drawdown, and minimum validation Sharpe.
- Drawdown ladder with current drawdown, warning threshold, block threshold, and kill-switch threshold.
- Exposure heatmap by symbol and sector.
- Correlation matrix with accessible heatmap colors.
- Rejected trade log with timestamp, symbol, agent reason, and risk rule.
- Manual pause, resume, and kill-switch controls with confirmation states.

Visual style:
- Institutional dark operations desk, compact risk console.
- Amber for warning zones, red only for blocked or killed states, green only for verified safe states.
- Dense tables, precise numeric cells, visible focus rings, no decorative hero areas.

Platform: desktop-first responsive web dashboard.
```

## Settings + Integrations

```text
Settings and integrations screen for a paper-trading AI operations dashboard.

Key features:
- Broker connection status for Alpaca paper account without showing raw API keys.
- Model provider status, token budget, cost budget, and replay cache state.
- MCP server registry with name, URL, enabled state, timeout, last health check, and error status.
- Export controls for audit logs, event streams, agent traces, and trade plans.
- Safety checklist showing paper-only mode, confirmation token requirement, and live-mode disabled state.

Visual style:
- Dark technical admin console, dense and controlled.
- Fira Code for integration IDs and status values, Fira Sans for labels.
- Violet only for intentional operator actions, amber for warnings, red for blocked states.
- Do not render secrets, tokens, or credential values.

Platform: desktop-first responsive web dashboard.
```