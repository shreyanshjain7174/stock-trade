import { useEffect, useMemo, useState } from 'react'
import './styles/tokens.css'
import './App.css'
import { fetchDashboardStatus, triggerKillSwitch, type DashboardStatus } from './api/client'
import { KillSwitchButton } from './components/KillSwitchButton'
import { ModeBadge } from './components/ModeBadge'
import { StatusPill } from './components/StatusPill'
import { mockDashboardStatus } from './data/mockDashboardStatus'
import { AgentTimeline } from './screens/AgentTimeline'
import { CommandCenter } from './screens/CommandCenter'
import { ResearchLab } from './screens/ResearchLab'
import { RiskCockpit } from './screens/RiskCockpit'
import { SettingsIntegrations } from './screens/SettingsIntegrations'

type LoadState = 'loading' | 'ready' | 'error'
type ScreenId = 'command' | 'timeline' | 'research' | 'risk' | 'settings'

const screens: Array<{ id: ScreenId; label: string }> = [
  { id: 'command', label: 'Command' },
  { id: 'timeline', label: 'Timeline' },
  { id: 'research', label: 'Research' },
  { id: 'risk', label: 'Risk' },
  { id: 'settings', label: 'Settings' },
]
const DASHBOARD_REFRESH_MS = 15_000

function App() {
  const [status, setStatus] = useState<DashboardStatus | null>(null)
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [killSwitchArmed, setKillSwitchArmed] = useState(false)
  const [activeScreen, setActiveScreen] = useState<ScreenId>('command')

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    const refreshDashboard = () => {
      fetchDashboardStatus(controller.signal)
        .then((nextStatus) => {
          if (active) {
            setStatus(nextStatus)
            setLoadState('ready')
          }
        })
        .catch(() => {
          if (active && !controller.signal.aborted) {
            setLoadState('error')
          }
        })
    }

    refreshDashboard()
    const intervalId = window.setInterval(refreshDashboard, DASHBOARD_REFRESH_MS)

    return () => {
      active = false
      window.clearInterval(intervalId)
      controller.abort()
    }
  }, [])

  const dashboard = status ?? mockDashboardStatus
  const riskAlerts = useMemo(
    () => dashboard.risk.alerts.filter((alert) => alert.severity !== 'info'),
    [dashboard.risk.alerts],
  )

  async function handleKillSwitchToggle() {
    if (!killSwitchArmed) {
      setKillSwitchArmed(true)
      return
    }
    try {
      const response = await triggerKillSwitch('operator dashboard')
      setKillSwitchArmed(response.state.mode === 'killed')
      setStatus((current) =>
        current
          ? {
              ...current,
              mode: response.state.mode,
              executionEnabled: response.execution_enabled,
            }
          : current,
      )
    } catch {
      setKillSwitchArmed(true)
    }
  }

  return (
    <main className="ops-shell" aria-busy={loadState === 'loading'}>
      <header className="status-bar" aria-label="Trading system status">
        <div className="identity-block">
          <span className="eyebrow">RALPH paper desk</span>
          <h1>Agentic Trading Command Center</h1>
        </div>
        <div className="status-cluster">
          <ModeBadge mode={dashboard.mode} />
          <StatusPill label="Broker" value={dashboard.brokerStatus} tone="neutral" />
          <StatusPill label="Data" value={dashboard.dataFreshness} tone="neutral" />
          <StatusPill
            label="Execution"
            value={dashboard.executionEnabled ? 'armed' : 'gated'}
            tone={dashboard.executionEnabled ? 'warning' : 'safe'}
          />
          <KillSwitchButton
            armed={killSwitchArmed}
            onToggle={() => {
              void handleKillSwitchToggle()
            }}
          />
        </div>
      </header>

      {loadState === 'error' ? (
        <section className="notice-panel" role="status">
          API unavailable. Showing mock operator data until the FastAPI service is running.
        </section>
      ) : null}

      <nav className="screen-tabs" aria-label="Dashboard screens">
        {screens.map((screen) => (
          <button
            type="button"
            key={screen.id}
            className={activeScreen === screen.id ? 'active' : ''}
            onClick={() => setActiveScreen(screen.id)}
          >
            {screen.label}
          </button>
        ))}
      </nav>

      {activeScreen === 'command' ? (
        <CommandCenter dashboard={dashboard} riskAlerts={riskAlerts} />
      ) : null}
      {activeScreen === 'timeline' ? <AgentTimeline timeline={dashboard.agentTimeline} /> : null}
      {activeScreen === 'research' ? <ResearchLab research={dashboard.research} /> : null}
      {activeScreen === 'risk' ? <RiskCockpit dashboard={dashboard} /> : null}
      {activeScreen === 'settings' ? <SettingsIntegrations dashboard={dashboard} /> : null}
    </main>
  )
}

export default App