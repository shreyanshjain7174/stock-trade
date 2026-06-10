interface KillSwitchButtonProps {
  armed: boolean
  onToggle: () => void
}

export function KillSwitchButton({ armed, onToggle }: KillSwitchButtonProps) {
  return (
    <button
      type="button"
      className={armed ? 'kill-switch armed' : 'kill-switch'}
      onClick={onToggle}
      aria-pressed={armed}
    >
      {armed ? 'Confirm kill switch' : 'Kill switch'}
    </button>
  )
}