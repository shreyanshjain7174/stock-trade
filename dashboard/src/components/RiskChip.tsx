interface RiskChipProps {
  label: string
  tone: 'info' | 'warning' | 'critical' | 'safe'
}

export function RiskChip({ label, tone }: RiskChipProps) {
  return <span className={`risk-chip ${tone}`}>{label}</span>
}