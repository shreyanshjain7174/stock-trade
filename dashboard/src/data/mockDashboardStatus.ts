import type { DashboardStatus } from '../api/client'

export const mockDashboardStatus: DashboardStatus = {
  mode: 'paper',
  executionEnabled: false,
  brokerStatus: 'paper linked',
  dataFreshness: 'fresh',
  account: {
    equity: 100000,
    cash: 50000,
    dailyPnl: 1240,
    drawdown: -0.034,
  },
  risk: {
    cashBufferPct: 0.1,
    exposurePct: 0.5,
    alerts: [
      { severity: 'warning', message: 'Execution is gated until confirmation token is supplied.' },
    ],
  },
  positions: [
    { symbol: 'SPY', marketValue: 25000, targetWeight: 0.25, drift: 0.004, lastDecision: 'approved' },
    { symbol: 'QQQ', marketValue: 25000, targetWeight: 0.25, drift: -0.002, lastDecision: 'resized' },
  ],
  openOrders: [],
  agentTimeline: [
    { name: 'Research', status: 'done', summary: 'Validation-only sweep found two active trend candidates.' },
    { name: 'Analyze', status: 'done', summary: 'Pseudo committee approved SPY and resized QQQ exposure.' },
    { name: 'Limit', status: 'done', summary: 'Cash buffer and max-position gates passed.' },
    { name: 'Plan', status: 'done', summary: 'Paper plan persisted with stable client order IDs.' },
  ],
  equityCurve: [62, 58, 55, 52, 44, 48, 42, 38, 35, 28, 22, 18],
}