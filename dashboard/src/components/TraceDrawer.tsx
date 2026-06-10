interface TraceDrawerProps {
  title: string
  children: React.ReactNode
}

export function TraceDrawer({ title, children }: TraceDrawerProps) {
  return (
    <details className="trace-drawer">
      <summary>{title}</summary>
      <div>{children}</div>
    </details>
  )
}