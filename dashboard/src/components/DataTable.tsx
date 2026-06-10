import { formatCurrency, formatPercent } from '../utils/format'
import type { DashboardStatus } from '../api/client'

interface DataTableProps {
  positions: DashboardStatus['positions']
}

export function DataTable({ positions }: DataTableProps) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Value</th>
            <th>Target</th>
            <th>Drift</th>
            <th>Decision</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((position) => (
            <tr key={position.symbol}>
              <td>{position.symbol}</td>
              <td>{formatCurrency(position.marketValue)}</td>
              <td>{formatPercent(position.targetWeight)}</td>
              <td>{formatPercent(position.drift)}</td>
              <td>{position.lastDecision}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}