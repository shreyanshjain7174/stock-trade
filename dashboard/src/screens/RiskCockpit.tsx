import { RiskChip } from '../components/RiskChip'
import { formatPercent } from '../utils/format'
import type { DashboardStatus } from '../api/client'

interface RiskCockpitProps {
  dashboard: DashboardStatus
}

export function RiskCockpit({ dashboard }: RiskCockpitProps) {
  return (
    <section className="screen-grid single-screen" aria-label="Risk Cockpit">
      <section className="panel surface-strong">
        <div className="panel-heading compact">
          <span className="eyebrow">Limit</span>
          <h2>Risk Cockpit</h2>
        </div>
        <div className="risk-limits-grid">
          <RiskLimit label="Cash buffer" value={formatPercent(dashboard.risk.cashBufferPct)} />
          <RiskLimit label="Exposure" value={formatPercent(dashboard.risk.exposurePct)} />
          <RiskLimit label="Drawdown" value={formatPercent(dashboard.account.drawdown)} />
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Rejected</span>
          <h2>Rejected trade log</h2>
        </div>
        <div className="alert warning">
          <span>blocked</span>
          <p>No live-mode adapter exists. Paper-only controls remain enforced.</p>
        </div>
        <RiskChip label="paper-only" tone="warning" />
      </section>
    </section>
  )
}

function RiskLimit({ label, value }: { label: string; value: string }) {
  return (
    <div className="risk-limit">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}