/* The socket state. Red is the dot; the word carries the meaning, so the
   indicator still reads with colour stripped out. */
export function Live({ on = true, label }) {
  return (
    <span className={`live ${on ? 'live-on' : 'live-off'}`}>
      <span className="live-dot" aria-hidden="true" />
      {label ?? (on ? 'Online' : 'Offline')}
    </span>
  )
}
