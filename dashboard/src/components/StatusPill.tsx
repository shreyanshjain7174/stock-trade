interface StatusPillProps {
  label: string
  value: string
  tone: string
}

export function StatusPill({ label, value, tone }: StatusPillProps) {
  return (
    <div className={`status-pill ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}