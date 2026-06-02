interface MetricCardProps {
  label: string
  value: string
  tone?: string
}

export function MetricCard({ label, value, tone = 'neutral' }: MetricCardProps) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}