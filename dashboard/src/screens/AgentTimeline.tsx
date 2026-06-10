import { StatusDot } from '../components/StatusDot'
import { TraceDrawer } from '../components/TraceDrawer'
import type { DashboardStatus } from '../api/client'

interface AgentTimelineProps {
  timeline: DashboardStatus['agentTimeline']
}

export function AgentTimeline({ timeline }: AgentTimelineProps) {
  return (
    <section className="screen-grid single-screen" aria-label="Agent Decision Timeline">
      <section className="panel surface-strong">
        <div className="panel-heading compact">
          <span className="eyebrow">Analyze</span>
          <h2>Agent Decision Timeline</h2>
        </div>
        <ol className="timeline timeline-expanded">
          {timeline.map((step) => (
            <li key={step.name}>
              <StatusDot tone={step.status} />
              <div>
                <strong>{step.name}</strong>
                <p>{step.summary}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section className="panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Trace</span>
          <h2>Tool calls</h2>
        </div>
        <TraceDrawer title="committee.review">
          <p>Reads leaderboard rows and emits approved, resized, rejected, or blocked decisions.</p>
        </TraceDrawer>
        <TraceDrawer title="risk.gate">
          <p>Persists the decision reason before a paper plan is available to the operator.</p>
        </TraceDrawer>
      </section>
    </section>
  )
}