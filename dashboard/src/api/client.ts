export interface DashboardStatus {
  mode: 'research' | 'paper' | 'blocked' | 'paused' | 'killed'
  executionEnabled: boolean
  brokerStatus: string
  dataFreshness: string
  account: {
    equity: number
    cash: number
    dailyPnl: number
    drawdown: number
  }
  risk: {
    cashBufferPct: number
    exposurePct: number
    alerts: Array<{ severity: 'info' | 'warning' | 'critical'; message: string }>
  }
  positions: Array<{
    symbol: string
    marketValue: number
    targetWeight: number
    drift: number
    lastDecision: string
  }>
  openOrders: Array<{
    id: string
    symbol: string
    notional: number
    status: string
  }>
  agentTimeline: Array<{
    name: string
    status: 'done' | 'blocked' | 'pending'
    summary: string
  }>
  equityCurve: number[]
}

interface ApiHealthResponse {
  mode: DashboardStatus['mode']
  execution_enabled: boolean
}

interface ApiAccountResponse {
  snapshot?: {
    equity?: number
    cash?: number
    daily_pnl?: number
    drawdown?: number
    mode?: string
  }
}

interface ApiRiskResponse {
  risk?: {
    cash_buffer_pct?: number
    max_position_pct?: number
    max_drawdown_pct?: number
  }
}

interface ApiPositionsResponse {
  positions?: Array<{ symbol?: string; market_value?: number; target_weight?: number }>
}

interface ApiOrdersResponse {
  orders?: Array<{ id?: string; symbol?: string; notional?: number; status?: string }>
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export async function fetchDashboardStatus(signal?: AbortSignal): Promise<DashboardStatus> {
  const [health, account, risk, positions, orders] = await Promise.all([
    getJson<ApiHealthResponse>('/health', signal),
    getJson<ApiAccountResponse>('/api/account/snapshot', signal),
    getJson<ApiRiskResponse>('/api/risk/status', signal),
    getJson<ApiPositionsResponse>('/api/positions', signal),
    getJson<ApiOrdersResponse>('/api/orders/open', signal),
  ])

  const equity = account.snapshot?.equity ?? 100000
  const mappedPositions = (positions.positions ?? []).map((position) => ({
    symbol: position.symbol ?? 'N/A',
    marketValue: position.market_value ?? 0,
    targetWeight: position.target_weight ?? 0,
    drift: 0,
    lastDecision: 'unknown',
  }))
  const exposurePct =
    equity > 0
      ? mappedPositions.reduce((total, position) => total + position.marketValue, 0) / equity
      : 0

  return {
    mode: health.mode,
    executionEnabled: health.execution_enabled,
    brokerStatus: account.snapshot?.mode === 'paper' ? 'paper linked' : 'offline',
    dataFreshness: 'fresh',
    account: {
      equity,
      cash: account.snapshot?.cash ?? 100000,
      dailyPnl: account.snapshot?.daily_pnl ?? 0,
      drawdown: account.snapshot?.drawdown ?? 0,
    },
    risk: {
      cashBufferPct: risk.risk?.cash_buffer_pct ?? 0.1,
      exposurePct,
      alerts: health.execution_enabled
        ? []
        : [{ severity: 'warning', message: 'Paper execution is gated by backend controls.' }],
    },
    positions: mappedPositions,
    openOrders: (orders.orders ?? []).map((order) => ({
      id: order.id ?? `${order.symbol ?? 'order'}-pending`,
      symbol: order.symbol ?? 'N/A',
      notional: order.notional ?? 0,
      status: order.status ?? 'open',
    })),
    agentTimeline: [
      { name: 'Research', status: 'pending', summary: 'Waiting for latest persisted RALPH cycle.' },
      { name: 'Analyze', status: 'pending', summary: 'Committee trace will appear after the next run.' },
      { name: 'Limit', status: 'pending', summary: 'Risk gate is idle.' },
    ],
    equityCurve: [64, 60, 59, 52, 48, 45, 44, 39, 35, 32, 30, 26],
  }
}

export async function triggerKillSwitch(reason: string): Promise<{
  mode: DashboardStatus['mode']
  execution_enabled: boolean
  state: { mode: DashboardStatus['mode']; reason?: string }
}> {
  return getJson('/api/system/kill-switch', undefined, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
}

async function getJson<T>(
  path: string,
  signal?: AbortSignal,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal })
  if (!response.ok) {
    throw new Error(`Request failed: ${path}`)
  }
  return (await response.json()) as T
}