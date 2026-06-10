interface StatusDotProps {
  tone: 'done' | 'blocked' | 'pending'
}

export function StatusDot({ tone }: StatusDotProps) {
  return <span className={`timeline-marker ${tone}`} aria-hidden="true" />
}