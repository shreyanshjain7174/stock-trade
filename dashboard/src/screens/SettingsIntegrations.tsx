import type { DashboardStatus } from '../api/client'

interface SettingsIntegrationsProps {
  dashboard: DashboardStatus
}

export function SettingsIntegrations({ dashboard }: SettingsIntegrationsProps) {
  return (
    <section className="screen-grid single-screen" aria-label="Settings and Integrations">
      <section className="panel surface-strong">
        <div className="panel-heading compact">
          <span className="eyebrow">Settings</span>
          <h2>Settings + Integrations</h2>
        </div>
        <div className="integration-list">
          <IntegrationRow label="Alpaca" value={dashboard.brokerStatus} />
          <IntegrationRow label="Model provider" value="not connected" />
          <IntegrationRow label="Replay cache" value="local ready" />
          <IntegrationRow label="MCP registry" value="manual Stitch workflow" />
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Safety</span>
          <h2>Credential policy</h2>
        </div>
        <p className="muted-copy">Connection status is visible. Raw keys, tokens, and secrets are never rendered.</p>
      </section>
    </section>
  )
}

function IntegrationRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="integration-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}