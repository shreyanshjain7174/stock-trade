import type { CSSProperties } from 'react'
import { DataTable } from '../components/DataTable'
import { EquityCurve } from '../components/EquityCurve'
import { MetricCard } from '../components/MetricCard'
import { formatCurrency, formatPercent } from '../utils/format'
import type { DashboardStatus } from '../api/client'

interface CommandCenterProps {
  dashboard: DashboardStatus
  riskAlerts: DashboardStatus['risk']['alerts']
}

export function CommandCenter({ dashboard, riskAlerts }: CommandCenterProps) {
  return (
    <section className="screen-grid command-grid" aria-label="Command Center">
      <section className="equity-panel panel surface-strong">
        <div className="panel-heading">
          <span className="eyebrow">Account</span>
          <h2>Paper equity</h2>
        </div>
        <div className="equity-value">{formatCurrency(dashboard.account.equity)}</div>
        <div className="metric-row">
          <MetricCard label="Cash buffer" value={formatPercent(dashboard.risk.cashBufferPct)} />
          <MetricCard label="Daily P&L" value={formatCurrency(dashboard.account.dailyPnl)} />
          <MetricCard label="Drawdown" value={formatPercent(dashboard.account.drawdown)} tone="warning" />
        </div>
        <EquityCurve points={dashboard.equityCurve} />
      </section>

      <section className="risk-panel panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Limit</span>
          <h2>Risk cockpit</h2>
        </div>
        <div
          className="risk-meter"
          style={{ '--risk-level': `${dashboard.risk.exposurePct * 100}%` } as CSSProperties}
        >
          <span>Exposure</span>
          <strong>{formatPercent(dashboard.risk.exposurePct)}</strong>
        </div>
        <div className="alert-stack">
          {riskAlerts.length > 0 ? (
            riskAlerts.map((alert) => (
              <div className={`alert ${alert.severity}`} key={alert.message}>
                <span>{alert.severity}</span>
                <p>{alert.message}</p>
              </div>
            ))
          ) : (
            <div className="alert safe">
              <span>safe</span>
              <p>No active risk blocks.</p>
            </div>
          )}
        </div>
      </section>

      <section className="positions-panel panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Plan</span>
          <h2>Positions</h2>
        </div>
        <DataTable positions={dashboard.positions} />
      </section>

      <section className="orders-panel panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Hand-off</span>
          <h2>Open orders</h2>
        </div>
        {dashboard.openOrders.length > 0 ? (
          dashboard.openOrders.map((order) => (
            <div className="order-row" key={order.id}>
              <span>{order.symbol}</span>
              <strong>{formatCurrency(order.notional)}</strong>
              <small>{order.status}</small>
            </div>
          ))
        ) : (
          <div className="empty-state">No open paper orders.</div>
        )}
      </section>
    </section>
  )
}