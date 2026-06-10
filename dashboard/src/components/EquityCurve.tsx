interface EquityCurveProps {
  points: number[]
}

export function EquityCurve({ points }: EquityCurveProps) {
  const polyline = points
    .map((point, index) => `${(index / Math.max(points.length - 1, 1)) * 100},${100 - point}`)
    .join(' ')

  return (
    <svg className="equity-curve" viewBox="0 0 100 100" role="img" aria-label="Paper equity trend">
      <polyline points={polyline} />
    </svg>
  )
}