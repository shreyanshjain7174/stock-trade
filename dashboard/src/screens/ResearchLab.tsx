import { RiskChip } from '../components/RiskChip'

const candidateRows = [
  { symbol: 'SPY', strategy: 'trend_sma_50_150', score: 0.6, holdout: 1.78, state: 'approved' },
  { symbol: 'QQQ', strategy: 'trend_sma_50_200', score: 0.3, holdout: 2.02, state: 'resized' },
]

export function ResearchLab() {
  return (
    <section className="screen-grid single-screen" aria-label="Research Lab">
      <section className="panel surface-strong">
        <div className="panel-heading compact">
          <span className="eyebrow">Research</span>
          <h2>Research Lab</h2>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Strategy</th>
                <th>Validation score</th>
                <th>Holdout Sharpe</th>
                <th>Gate</th>
              </tr>
            </thead>
            <tbody>
              {candidateRows.map((candidate) => (
                <tr key={`${candidate.symbol}-${candidate.strategy}`}>
                  <td>{candidate.symbol}</td>
                  <td>{candidate.strategy}</td>
                  <td>{candidate.score.toFixed(2)}</td>
                  <td>{candidate.holdout.toFixed(2)} report-only</td>
                  <td>
                    <RiskChip label={candidate.state} tone="safe" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading compact">
          <span className="eyebrow">Artifacts</span>
          <h2>Backtest evidence</h2>
        </div>
        <p className="muted-copy">Holdout metrics are shown for audit only and never used for selection.</p>
      </section>
    </section>
  )
}