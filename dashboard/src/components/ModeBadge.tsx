import type { DashboardStatus } from '../api/client'
import { StatusPill } from './StatusPill'

interface ModeBadgeProps {
  mode: DashboardStatus['mode']
}

export function ModeBadge({ mode }: ModeBadgeProps) {
  const tone = mode === 'paper' ? 'paper' : 'research'

  return <StatusPill label="Mode" value={mode} tone={tone} />
}